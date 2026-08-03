"""
1단계: 위키 순회 수집

Notion API의 Get Block Children은 1단계 자식만 반환하므로
페이지 트리 전체를 얻으려면 자식 블록마다 재귀 호출해야 한다.
초당 약 3요청의 레이트리밋이 있어 429 발생 시 백오프 재시도가 필요하다.
"""

from dataclasses import dataclass

from notion_client import Client
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


@dataclass
class WikiBlock:
    block_id: str
    block_type: str          # "paragraph" | "heading_1" | "pdf" | "file" | ... 등
    text: str | None         # 텍스트 블록이면 내용, 아니면 None
    attachment_url: str | None  # 파일/PDF 블록이면 (만료되는) 다운로드 URL
    attachment_name: str | None


class NotionWikiCrawler:
    def __init__(self, api_key: str):
        self.client = Client(auth=api_key)

    def collect_all_blocks(self, root_page_id: str) -> list[WikiBlock]:
        """
        SUDO:
          blocks = []
          walk(root_page_id, blocks)
          return blocks
        """
        blocks: list[WikiBlock] = []
        self._walk(root_page_id, blocks)
        return blocks

    def _walk(self, block_id: str, acc: list[WikiBlock]) -> None:
        """
        SUDO:
          children = get_children_with_backoff(block_id)  # 페이지네이션 포함
          for child in children:
              wb = to_wiki_block(child)
              acc.append(wb)
              if child.has_children:
                  _walk(child.id, acc)   # 재귀
        """
        for child in self._get_children_with_backoff(block_id):
            acc.append(self._to_wiki_block(child))
            if child.get("has_children"):
                self._walk(child["id"], acc)

    @retry(
        retry=retry_if_exception_type(Exception),  # TODO: notion_client의 RateLimitedError로 좁히기
        wait=wait_exponential(multiplier=1, min=1, max=60),
        stop=stop_after_attempt(6),
    )
    def _get_children_with_backoff(self, block_id: str) -> list[dict]:
        """
        SUDO:
          results = []
          cursor = None
          loop:
              resp = client.blocks.children.list(block_id, start_cursor=cursor)
              results += resp["results"]
              if not resp["has_more"]: break
              cursor = resp["next_cursor"]
          return results
        """
        raise NotImplementedError

    def _to_wiki_block(self, raw_block: dict) -> WikiBlock:
        """
        SUDO:
          type = raw_block["type"]
          if type in TEXT_TYPES:      # paragraph, heading_*, bulleted_list_item, ...
              text = extract_rich_text(raw_block[type]["rich_text"])
              return WikiBlock(id, type, text, None, None)
          elif type in {"pdf", "file"}:
              url = raw_block[type]["file"]["url"]  # 만료 URL, 즉시 다운로드 필요
              name = raw_block[type].get("name")
              return WikiBlock(id, type, None, url, name)
          else:
              return WikiBlock(id, type, None, None, None)  # 무시 대상
        """
        raise NotImplementedError
