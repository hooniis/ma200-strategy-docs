#!/usr/bin/env python3
"""
introduction.mdx 의 '현재 상황 대시보드' 섹션과 dashboard-chart.png 를
최신 TQQQ 데이터로 갱신합니다.

사용법:
    cd docs
    python scripts/update-dashboard.py

필요 패키지: yfinance, pandas, matplotlib
"""
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DOCS_DIR = Path(__file__).parent.parent
MDX_PATH = DOCS_DIR / "dashboard.mdx"
IMG_1Y = DOCS_DIR / "images" / "dashboard-chart-1y.png"
IMG_1M = DOCS_DIR / "images" / "dashboard-chart-1m.png"

def fetch_data():
    t = yf.download('TQQQ', period='2y', progress=False, auto_adjust=True)['Close'].squeeze().dropna()
    ma200 = t.rolling(200).mean()
    return t, ma200

def build_state(t, ma200):
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

def draw_chart(t, ma200, s, days, out_path, title_range):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    t1 = t.iloc[-days:]
    ma1 = ma200.iloc[-days:]
    env1 = ma1 * 1.05

    fig, ax = plt.subplots(figsize=(12, 5.5), dpi=130)
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#fafafa')

    ax.plot(t1.index, t1.values, color='#1f77b4', linewidth=1.8, label='TQQQ')
    ax.plot(ma1.index, ma1.values, color='#d62728', linewidth=1.6, label='MA200')
    ax.plot(env1.index, env1.values, color='#ff7f0e', linewidth=1.2, linestyle='--', label='MA200 +5% (overheat)')

    # current price marker
    ax.scatter([t1.index[-1]], [s['price']], color='#ffd700', s=120,
               zorder=5, edgecolor='#333', linewidth=1.2, label=f"Now ${s['price']}")

    ax.fill_between(t1.index, ma1.values, env1.values,
                    color='#ff7f0e', alpha=0.08)

    situation_en = {'🟦 하락 상황': 'BEAR (below MA200)',
                    '🟥 집중 투자 상황': 'BULL (MA200 ~ +5%)',
                    '🟧 과열 상황': 'OVERHEAT (> MA200 +5%)'}.get(s['situation'], s['situation'])
    ax.set_title(f"TQQQ vs 200-day MA  |  {title_range}  |  {situation_en}  |  {s['date']}",
                 fontsize=14, fontweight='bold', pad=14)
    ax.set_ylabel('Price ($)', fontsize=10)
    ax.grid(True, linestyle=':', alpha=0.4)
    ax.legend(loc='upper left', framealpha=0.9, fontsize=9)

    if days <= 30:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    else:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax.get_xticklabels(), rotation=0, ha='center')

    plt.tight_layout()
    plt.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"✅ 차트 저장: {out_path}")

def build_section(s):
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

### 📉 200일선 차트

<Frame caption="최근 1년">
  <img src="/images/dashboard-chart-1y.png" alt="TQQQ 200-day MA (1Y)" />
</Frame>

<Frame caption="최근 1개월">
  <img src="/images/dashboard-chart-1m.png" alt="TQQQ 200-day MA (1M)" />
</Frame>

<Tip>
차트는 매일 평일 미국장 마감 후 자동 갱신됩니다. 파란 선은 TQQQ 종가, 빨간 선은 200일선, 주황 점선은 과열선(200MA +5%)입니다.
</Tip>

### 🛒 주문하기

<Card title="토스증권에서 TQQQ 주문" icon="cart-shopping" href="https://www.tossinvest.com/stocks/US20100211003/order">
  현재 신호에 맞춰 바로 주문 페이지로 이동
</Card>

---
"""

def send_telegram(state):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("ℹ️ TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID 미설정 → 전송 생략")
        return
    s = state
    text = (
        f"📊 *200일선 매매법 오늘의 알림*\n"
        f"🗓 {s['date']}\n\n"
        f"{s['situation']}\n"
        f"➡️ *{s['action']}*\n\n"
        f"• TQQQ 종가: *${s['price']}* ({s['daily_ret']:+.2f}%)\n"
        f"• 200일선: ${s['ma200']}\n"
        f"• 과열선(+5%): ${s['envelope']}\n"
        f"• 200일선 대비: *{s['diff_pct']:+.2f}%* {s['diff_emoji']}\n"
        f"• 52주 고/저: ${s['high52']} / ${s['low52']}\n\n"
        f"🔗 [대시보드](https://hooniis.mintlify.app/dashboard) · "
        f"[주문](https://www.tossinvest.com/stocks/US20100211003/order)"
    )
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": "true",
    }).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=10) as r:
            print(f"✅ 텔레그램 전송: {r.status}")
    except Exception as e:
        print(f"⚠️ 텔레그램 전송 실패: {e}")

def main():
    t, ma200 = fetch_data()
    state = build_state(t, ma200)
    print(f"현재 상태: {state['situation']} (TQQQ ${state['price']}, 200MA ${state['ma200']}, 괴리 {state['diff_pct']:+.2f}%)")

    draw_chart(t, ma200, state, 252, IMG_1Y, "1Y")
    draw_chart(t, ma200, state, 22, IMG_1M, "1M")

    content = MDX_PATH.read_text(encoding='utf-8')
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

    send_telegram(state)

if __name__ == "__main__":
    main()
