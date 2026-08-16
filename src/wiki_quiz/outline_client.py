"""
1단계: 위키 순회 수집

Outline API는 RPC 스타일의 POST 엔드포인트로 구성된다(REST가 아님).
`collections.list`로 컬렉션 목록을 얻고, 각 컬렉션에 속한 문서는
`documents.list`(컬렉션/부모 문서 기준 자식 목록)로 얻은 뒤, 본문이 필요하면
`documents.info`를 호출해 Markdown 본문을 받는다. 자식 문서가 있으면 같은 방식으로
재귀 호출해 트리 전체를 순회한다.

인증은 `Authorization: Bearer <API Key>` 헤더(Settings → API Keys에서 발급).

레이트리밋: Notion처럼 "초당 N req" 같은 고정 공식 수치가 없고, 자체 호스팅 인스턴스의
rate limiter 설정에 따른다(공식 문서 예시는 인스턴스 전체 기준 IP당 분당 1000 req 수준이나
설치별로 조정 가능한 기본값일 뿐, `wiki.class.day` 인스턴스의 실제 설정은 미확인).
429 발생 시 백오프 재시도가 필요하다.

※ 참고: https://www.getoutline.com/developers , https://docs.getoutline.com/s/hosting/doc/rate-limiter-HSqErsUgXH

구현 메모 (스켈레톤 → 구현 전환 시 결정한 사항):
- `documents.list`는 `offset`/`limit` 페이지네이션으로 순회한다. 응답 개수가 `limit`보다
  적으면 마지막 페이지로 판단한다.
- 재시도 조건을 "모든 Exception"에서 `httpx.HTTPStatusError`이면서 status_code == 429인
  경우로 좁혔다. 인증 오류(401/403) 같은 비일시적 오류까지 최대 6회(최대 약 63초)
  재시도하며 시간을 낭비하지 않기 위함.
- 첨부파일 링크는 Markdown 링크/이미지 문법(`[..](url)`, `![..](url)`)에서 URL을 추출하고,
  확장자가 pdf/docx/doc/md/markdown인 것만 첨부파일 후보로 남겨 일반 하이퍼링크 노이즈를
  제거한다. 실제 첨부 URL이 서명된 만료 URL인지 인증 프록시 URL인지는 README에 남긴 대로
  미확인이므로, attachment_parser 쪽에 인증 토큰을 실어 보낼 수 있는 경로를 열어뒀다
  (main.py에서 outline_api_key를 전달).
"""

import re
from dataclasses import dataclass, field

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

# Markdown 링크/이미지 문법에서 URL만 추출: ![alt](url) 또는 [text](url)
_MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\((https?://[^\s)]+)\)")

# 첨부파일로 취급할 확장자 (attachment_parser.py가 실제로 파싱 가능한 포맷과 맞춘다)
_ATTACHMENT_EXTENSIONS = (".pdf", ".docx", ".doc", ".md", ".markdown")


@dataclass
class WikiDocument:
    document_id: str
    title: str
    text: str | None            # 문서 본문 (Markdown)
    parent_document_id: str | None
    collection_id: str
    attachment_urls: list[str] = field(default_factory=list)  # 본문 안에 임베드된 첨부파일 링크


def _raise_with_body(resp: httpx.Response) -> None:
    """4xx/5xx 응답 시 Outline이 돌려주는 {"ok": false, "error": "..."} 본문을
    예외 메시지에 포함시켜, 로그만 보고도 원인(잘못된 파라미터 등)을 바로 알 수 있게 한다.
    """
    if resp.is_success:
        return
    try:
        detail = resp.json()
    except ValueError:
        detail = resp.text
    raise httpx.HTTPStatusError(
        f"{resp.status_code} {resp.reason_phrase} for url '{resp.url}': {detail!r}",
        request=resp.request,
        response=resp,
    )


def _is_rate_limited(exc: BaseException) -> bool:
    """429(Too Many Requests) 응답에 대해서만 재시도한다.

    스켈레톤 TODO("모든 Exception 재시도")를 좁힌 부분: 인증 실패나 잘못된 요청 같은
    비일시적 오류까지 여러 번 재시도하며 시간을 버리지 않도록 한다.
    """
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429


_outline_retry = retry(
    retry=retry_if_exception(_is_rate_limited),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(6),
    reraise=True,
)


class OutlineWikiCrawler:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self.api_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30.0,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "OutlineWikiCrawler":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def collect_all_documents(self, root_collection_id: str) -> list[WikiDocument]:
        docs: list[WikiDocument] = []
        self._walk(parent_document_id=None, collection_id=root_collection_id, acc=docs)
        return docs

    def collect_document_tree(self, root_document_id: str) -> list[WikiDocument]:
        """단일 문서를 루트로, 그 문서와 하위 문서 트리만 수집한다.

        컬렉션 전체가 아니라 지정된 문서 하나(+그 자식들)만 퀴즈 소스로 쓰고 싶을 때 사용.
        """
        info = self._fetch_document_info_with_backoff(root_document_id)
        root_doc = self._to_wiki_document(info)
        docs: list[WikiDocument] = [root_doc]
        # root_document_id는 URL slug일 수 있어 documents.list가 거부할 수 있다(400).
        # documents.info 응답의 실제 UUID(root_doc.document_id)를 대신 사용한다.
        self._walk(parent_document_id=root_doc.document_id, collection_id=root_doc.collection_id, acc=docs)
        return docs

    def _walk(self, parent_document_id: str | None, collection_id: str, acc: list[WikiDocument]) -> None:
        for child in self._list_documents_with_backoff(collection_id, parent_document_id):
            info = self._fetch_document_info_with_backoff(child["id"])
            acc.append(self._to_wiki_document(info))
            # 자식 문서가 없으면 documents.list가 빈 목록을 반환해 재귀가 자연스럽게 끝난다.
            self._walk(child["id"], collection_id, acc)

    @_outline_retry
    def _list_documents_with_backoff(self, collection_id: str, parent_document_id: str | None) -> list[dict]:
        results: list[dict] = []
        offset = 0
        limit = 100
        while True:
            resp = self._http.post(
                "/documents.list",
                json={
                    "collectionId": collection_id,
                    "parentDocumentId": parent_document_id,
                    "offset": offset,
                    "limit": limit,
                },
            )
            _raise_with_body(resp)
            payload = resp.json()
            data = payload.get("data", [])
            results.extend(data)
            if len(data) < limit:
                break
            offset += limit
        return results

    @_outline_retry
    def _fetch_document_info_with_backoff(self, document_id: str) -> dict:
        resp = self._http.post("/documents.info", json={"id": document_id})
        _raise_with_body(resp)
        return resp.json()["data"]

    def _to_wiki_document(self, raw: dict) -> WikiDocument:
        text = raw.get("text") or ""
        return WikiDocument(
            document_id=raw["id"],
            title=raw.get("title", ""),
            text=text,
            parent_document_id=raw.get("parentDocumentId"),
            collection_id=raw["collectionId"],
            attachment_urls=self._extract_attachment_urls(text),
        )

    @staticmethod
    def _extract_attachment_urls(text: str) -> list[str]:
        if not text:
            return []
        seen: dict[str, None] = {}
        for url in _MARKDOWN_LINK_RE.findall(text):
            clean = url.split("?", 1)[0].lower()
            if clean.endswith(_ATTACHMENT_EXTENSIONS):
                seen.setdefault(url, None)
        return list(seen.keys())
