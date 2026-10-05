"""
개념 설명 + 퀴즈를 정리본 형식의 파일(HTML 또는 Markdown)로 렌더링한다.

구성은 팀의 스터디 정리본(classday-infra-security-final.html)을 따른다:
제목/날짜 → 핵심 개념 → 퀴즈(정답은 펼쳐야 보임) → 출처.
HTML은 외부 의존성 없는 단일 파일이며, LLM이 만든 문자열은 모두 html.escape 한다.
"""

from datetime import date
from html import escape

from wiki_quiz.quiz_generator import QuizQuestion

_CSS = """
:root{--bg:#0d1117;--panel:#151b23;--panel2:#1c232c;--border:#2a323d;--text:#e6edf3;--muted:#9aa7b5;
--accent:#58a6ff;--net:#3fb950;--warn-bg:#3a2a12;--warn-bd:#7a5a1e;--warn-tx:#f0c674;
--good-bg:#0f2a1c;--good-bd:#1e5c3e;--good-tx:#7ee2a8;}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--text);line-height:1.75;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Pretendard,Arial,sans-serif;}
.shell{display:flex;min-height:100vh;}
nav.sidebar{width:230px;flex:0 0 230px;background:var(--panel);border-right:1px solid var(--border);
position:sticky;top:0;height:100vh;overflow-y:auto;padding:28px 14px 60px;}
.sidebar-logo{font-size:11px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;
color:var(--accent);margin-bottom:20px;line-height:1.6;}
.sidebar-logo span{display:block;color:var(--muted);font-weight:400;font-size:10.5px;margin-top:2px;}
nav.sidebar a{display:block;font-size:12.5px;color:var(--muted);text-decoration:none;
padding:5px 8px;border-radius:6px;margin-bottom:1px;}
nav.sidebar a:hover{background:var(--panel2);color:var(--text);}
main{flex:1;padding:44px 52px 100px;max-width:860px;}
@media(max-width:760px){.shell{flex-direction:column;}
nav.sidebar{width:100%;height:auto;position:static;}main{padding:24px 20px 80px;}}
.hero{padding-bottom:28px;border-bottom:1px solid var(--border);margin-bottom:36px;}
.kicker{color:var(--accent);font-weight:700;letter-spacing:.08em;font-size:12px;
text-transform:uppercase;margin-bottom:8px;}
h1{font-size:26px;line-height:1.3;margin:0 0 10px;}
.hero-meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;}
.hero-meta span{font-size:12px;color:var(--muted);background:var(--panel);
border:1px solid var(--border);padding:3px 10px;border-radius:999px;}
h2{font-size:20px;padding-bottom:10px;margin:52px 0 18px;border-bottom:2px solid var(--border);
display:flex;align-items:center;gap:10px;}
h2 .num{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;
border-radius:50%;background:var(--accent);color:#04121f;font-size:13px;font-weight:800;flex:0 0 auto;}
.card{background:var(--panel);border:1px solid var(--border);border-left:4px solid var(--accent);
border-radius:10px;padding:15px 19px;margin:14px 0;}
.card h4{margin:0 0 6px;font-size:14px;} .card p{margin:0;font-size:14.5px;}
.warn{background:var(--warn-bg);border:1px solid var(--warn-bd);color:var(--warn-tx);
border-radius:10px;padding:13px 17px;margin:14px 0;font-size:14px;}
.good{background:var(--good-bg);border:1px solid var(--good-bd);color:var(--good-tx);
border-radius:10px;padding:13px 17px;margin:14px 0;font-size:14px;}
details.quiz{background:var(--panel);border:1px solid var(--border);border-radius:10px;
padding:14px 18px;margin:12px 0;}
details.quiz summary{cursor:pointer;font-weight:600;list-style:none;display:flex;
align-items:baseline;gap:8px;font-size:14.5px;}
details.quiz summary::-webkit-details-marker{display:none;}
details.quiz summary::before{content:"\\25B8";color:var(--accent);transition:transform .15s;}
details.quiz[open] summary::before{transform:rotate(90deg);}
.opts{margin:12px 0 4px;color:var(--muted);font-size:14px;} .opts div{margin:5px 0;}
.answer{margin-top:12px;padding-top:12px;border-top:1px dashed var(--border);font-size:14px;}
.answer .correct{color:var(--net);font-weight:800;}
.src{font-size:12px;color:var(--muted);margin-top:6px;}
footer{margin-top:60px;padding-top:20px;border-top:1px solid var(--border);
color:var(--muted);font-size:12px;line-height:1.8;}
"""


def _concepts(questions) -> list:
    return list(getattr(questions, "concepts", []) or [])


def _sources(questions: list[QuizQuestion]) -> list[str]:
    return sorted({q.source for q in questions})


def render_html(questions: list[QuizQuestion], today: date | None = None) -> str:
    today = today or date.today()
    concepts = _concepts(questions)
    sources = ", ".join(escape(s) for s in _sources(questions))

    sections = []  # (id, 제목, html)
    if concepts:
        cards = "\n".join(
            f'<div class="card"><h4>{i}. {escape(c.title)}</h4><p>{escape(c.explanation)}</p></div>'
            for i, c in enumerate(concepts, start=1)
        )
        sections.append(("s1", "핵심 개념", cards))
    quiz = "\n".join(_html_question(i, q) for i, q in enumerate(questions, start=1))
    sections.append((
        f"s{len(sections) + 1}", f"퀴즈 {len(questions)}문제",
        '<div class="warn"><b>먼저 스스로 답을 고른 뒤</b> 펼쳐서 확인하세요.</div>\n' + quiz,
    ))
    sections.append((
        f"s{len(sections) + 1}", "출처",
        f'<div class="good"><b>근거 문서</b> — {sources}</div>',
    ))

    nav = "\n".join(
        f'  <a href="#{sid}">{n}. {escape(title)}</a>' for n, (sid, title, _) in enumerate(sections, start=1)
    )
    main = "\n".join(
        f'<h2 id="{sid}"><span class="num">{n}</span>{escape(title)}</h2>\n{html}'
        for n, (sid, title, html) in enumerate(sections, start=1)
    )
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>오늘의 위키 퀴즈 — {today.isoformat()}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="shell">
<nav class="sidebar">
  <div class="sidebar-logo">Daily Wiki Quiz<span>{today.isoformat()}</span></div>
{nav}
</nav>
<main>
<div class="hero">
  <div class="kicker">Daily Wiki Quiz</div>
  <h1>오늘의 위키 퀴즈</h1>
  <div class="hero-meta"><span>📅 {today.isoformat()}</span><span>📝 {len(questions)}문제</span></div>
</div>
{main}
<footer>매일 위키 문서를 바탕으로 자동 생성된 학습 자료입니다.</footer>
</main>
</div>
</body>
</html>
"""


def _html_question(i: int, q: QuizQuestion) -> str:
    opts = "\n".join(
        f"    <div>{chr(ord('A') + j)}. {escape(c)}</div>" for j, c in enumerate(q.choices)
    )
    letter = chr(ord("A") + q.answer_index)
    return f"""<details class="quiz">
  <summary>Q{i}. {escape(q.question)}</summary>
  <div class="opts">
{opts}
  </div>
  <div class="answer"><span class="correct">정답: {letter}</span> — {escape(q.choices[q.answer_index])}<br>{escape(q.explanation)}
    <div class="src">출처: {escape(q.source)}</div></div>
</details>"""


def render_markdown(questions: list[QuizQuestion], today: date | None = None) -> str:
    today = today or date.today()
    lines = [f"# 오늘의 위키 퀴즈 — {today.isoformat()}", ""]
    concepts = _concepts(questions)
    if concepts:
        lines += ["## 핵심 개념", ""]
        for i, c in enumerate(concepts, start=1):
            lines += [f"### {i}. {c.title}", c.explanation, ""]
    lines += [f"## 퀴즈 {len(questions)}문제", ""]
    for i, q in enumerate(questions, start=1):
        lines += [f"**Q{i}. {q.question}**", ""]
        lines += [f"- {chr(ord('A') + j)}. {c}" for j, c in enumerate(q.choices)]
        letter = chr(ord("A") + q.answer_index)
        lines += [
            "",
            "<details><summary>정답 보기</summary>",
            "",
            f"**정답: {letter}. {q.choices[q.answer_index]}** — {q.explanation} (출처: {q.source})",
            "",
            "</details>",
            "",
        ]
    lines += ["---", "출처: " + ", ".join(_sources(questions)), ""]
    return "\n".join(lines)
