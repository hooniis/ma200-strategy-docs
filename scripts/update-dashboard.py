#!/usr/bin/env python3
"""
introduction.mdx 의 '현재 상황 대시보드' 섹션을 최신 TQQQ 데이터로 갱신합니다.

사용법:
    cd docs
    python scripts/update-dashboard.py

필요 패키지: yfinance, pandas
"""
import re
from pathlib import Path
import yfinance as yf

MDX_PATH = Path(__file__).parent.parent / "introduction.mdx"

def fetch_state():
    t = yf.download('TQQQ', period='2y', progress=False, auto_adjust=True)['Close'].squeeze().dropna()
    ma200 = t.rolling(200).mean()
    price = float(t.iloc[-1])
    ma = float(ma200.iloc[-1])
    envelope = ma * 1.05
    diff_pct = (price/ma - 1) * 100
    daily_ret = (t.iloc[-1]/t.iloc[-2] - 1) * 100
    high52 = float(t.iloc[-252:].max())
    low52 = float(t.iloc[-252:].min())

    if price < ma:
        situation, icon, action, diff_emoji = (
            "🟦 하락 상황", "arrow-trend-down",
            "SGOV 100% 보유 (현금 대피)", "🔴")
    elif price < envelope:
        situation, icon, action, diff_emoji = (
            "🟥 집중 투자 상황", "arrow-trend-up",
            "TQQQ 매수 / SPYM 유지", "🟢")
    else:
        situation, icon, action, diff_emoji = (
            "🟧 과열 상황", "fire",
            "TQQQ 유지, 신규자금은 SPYM", "🟡")

    return {
        "date": t.index[-1].strftime('%Y-%m-%d'),
        "price": round(price, 2),
        "ma200": round(ma, 2),
        "envelope": round(envelope, 2),
        "diff_pct": round(diff_pct, 2),
        "daily_ret": round(daily_ret, 2),
        "high52": round(high52, 2),
        "low52": round(low52, 2),
        "situation": situation,
        "icon": icon,
        "action": action,
        "diff_emoji": diff_emoji,
    }

def build_section(s):
    signal_line = (
        f"$${s['price']} < ${s['ma200']}  →  {s['situation']}"
        if s['price'] < s['ma200']
        else (
            f"${s['price']} > ${s['ma200']}  →  {s['situation']}"
            if s['price'] < s['envelope']
            else f"${s['price']} > ${s['envelope']}  →  {s['situation']}"
        )
    )

    return f"""## 📊 현재 상황 대시보드

<Info>
**스냅샷 기준일:** {s['date']} · 매일 평일 07:00(KST) GitHub Actions로 자동 갱신
</Info>

### 🎯 오늘의 신호

<CardGroup cols={{2}}>
  <Card title="{s['situation']}" icon="{s['icon']}">
    **권장 행동: {s['action']}**
  </Card>
  <Card title="TQQQ 현재가" icon="dollar-sign">
    **${s['price']}** ({s['daily_ret']:+.2f}%)
    200일선 대비 **{s['diff_pct']:+.2f}%**
  </Card>
</CardGroup>

### 📈 주요 수치

| 항목 | 값 |
|---|---:|
| **TQQQ 종가** | ${s['price']} |
| **200일 이동평균선** | ${s['ma200']} |
| **과열선 (200MA +5%)** | ${s['envelope']} |
| **200일선 대비 괴리** | **{s['diff_pct']:+.2f}%** {s['diff_emoji']} |
| **52주 최고가** | ${s['high52']} |
| **52주 최저가** | ${s['low52']} |

### 📉 라이브 차트 (TradingView)

<Frame>
  <iframe
    src="https://s.tradingview.com/widgetembed/?frameElementId=tv_chart&symbol=NASDAQ%3ATQQQ&interval=D&hidesidetoolbar=0&symboledit=1&saveimage=1&studies=%5B%22MASimple%40tv-basicstudies%22%5D&theme=light&style=1&timezone=Asia%2FSeoul&withdateranges=1&showpopupbutton=1&locale=kr"
    width="100%"
    height="500"
    frameBorder="0"
    allowTransparency="true"
    scrolling="no"
  />
</Frame>

<Tip>
차트에 **Moving Average** 지표를 200으로 설정하면 전략 기준선이 그대로 보입니다.
</Tip>

---
"""

def main():
    state = fetch_state()
    print(f"현재 상태: {state['situation']} (TQQQ ${state['price']}, 200MA ${state['ma200']}, 괴리 {state['diff_pct']:+.2f}%)")

    content = MDX_PATH.read_text(encoding='utf-8')
    # 대시보드 섹션 교체: '## 📊 현재 상황 대시보드' ~ 다음 '## 한 줄 요약' 직전 '---' 까지
    new_section = build_section(state)
    pattern = re.compile(
        r"## 📊 현재 상황 대시보드.*?---\n",
        re.DOTALL
    )
    if pattern.search(content):
        content = pattern.sub(new_section, content, count=1)
    else:
        print("⚠️ 대시보드 섹션을 찾을 수 없어 삽입을 건너뜁니다.")
        return
    MDX_PATH.write_text(content, encoding='utf-8')
    print(f"✅ 업데이트 완료: {MDX_PATH}")

if __name__ == "__main__":
    main()
