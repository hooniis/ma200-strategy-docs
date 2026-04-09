#!/usr/bin/env python3
"""
Toss 증권 TQQQ 커뮤니티 인기글 Top 5를 스크랩해서
dashboard.mdx 의 TOSS_POSTS 마커 구간을 갱신한다.

필요: playwright (+ chromium)
    python -m pip install playwright
    python -m playwright install chromium
"""
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://www.tossinvest.com/stocks/US20100211003/community"
MDX_PATH = Path(__file__).parent.parent / "dashboard.mdx"
START = "{/* TOSS_POSTS_START */}"
END = "{/* TOSS_POSTS_END */}"

async def fetch_posts(limit=5):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            locale="ko-KR",
            viewport={"width": 1440, "height": 900},
        )
        page = await ctx.new_page()
        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_selector('[data-section-name="커뮤니티__게시글"]', timeout=20000)
        await page.wait_for_timeout(1500)
        raw = await page.evaluate("""
            () => Array.from(
              document.querySelectorAll('[data-post-anchor-id]')
            ).slice(0, 8).map(n => ({
              id: n.getAttribute('data-post-anchor-id'),
              text: n.innerText || ''
            }))
        """)
        await browser.close()
    return raw[:limit]

def parse(item):
    post_id = item["id"]
    text = item["text"]
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # skip leading '주주'
    if lines and lines[0] == "주주":
        lines = lines[1:]
    if not lines:
        return None
    author = lines[0]
    time_line = lines[1] if len(lines) > 1 else ""
    time = time_line.split("・")[0].strip()
    # drop known chrome lines
    body = [l for l in lines[2:] if l not in ("팔로우", "팔로잉", "... 더 보기")]
    # trailing likes & comments (last two numeric)
    likes = comments = None
    if len(body) >= 2 and body[-1].isdigit() and body[-2].isdigit():
        comments = body[-1]
        likes = body[-2]
        body = body[:-2]
    elif len(body) >= 1 and body[-1].isdigit():
        likes = body[-1]
        body = body[:-1]
    content = " · ".join(body) if body else "(내용 없음)"
    if len(content) > 60:
        content = content[:60] + "…"
    return {
        "url": f"https://www.tossinvest.com/community/posts/{post_id}",
        "author": author,
        "time": time,
        "content": content,
    }

def render(posts):
    lines = ["### 💬 토스 커뮤니티 인기글 Top 5", "",
             "| 작성자 | 시간 | 내용 |",
             "|---|---|---|"]
    for p in posts:
        c = p["content"].replace("|", "\\|").replace("[", "〔").replace("]", "〕")
        lines.append(f"| {p['author']} | {p['time']} | [{c}]({p['url']}) |")
    lines += ["",
              '<Card title="토스 커뮤니티에서 더 보기" icon="comments" href="https://www.tossinvest.com/stocks/US20100211003/community">',
              "  전체 글 및 최신 의견 확인",
              "</Card>", ""]
    return "\n".join(lines)

async def main():
    raw = await fetch_posts(limit=5)
    posts = [p for p in (parse(r) for r in raw) if p]
    print(f"추출 {len(posts)}건")
    for p in posts:
        print(f"- [{p['time']}] {p['author']}: {p['content'][:40]} → {p['url']}")

    section = render(posts)

    content = MDX_PATH.read_text(encoding="utf-8")
    block = f"{START}\n{section}\n{END}"
    if START in content and END in content:
        pattern = re.compile(
            re.escape(START) + r".*?" + re.escape(END),
            re.DOTALL,
        )
        content = pattern.sub(block, content, count=1)
    else:
        # 첫 실행: 토스 주문 카드 뒤에 삽입
        anchor = "### 🛒 주문하기"
        idx = content.find(anchor)
        if idx < 0:
            print("⚠️ 앵커를 찾지 못했습니다. 파일 말미에 추가합니다.")
            content += "\n\n" + block + "\n"
        else:
            # insert before the anchor
            content = content[:idx] + block + "\n\n" + content[idx:]
    MDX_PATH.write_text(content, encoding="utf-8")
    print(f"✅ 업데이트 완료: {MDX_PATH}")

if __name__ == "__main__":
    asyncio.run(main())
