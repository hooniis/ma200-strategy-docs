#!/usr/bin/env python3
"""
introduction.mdx 의 '현재 상황 대시보드' 섹션과 dashboard-chart.png 를
최신 TQQQ 데이터로 갱신합니다.

사용법:
    cd docs
    python scripts/update-dashboard.py

필요 패키지: yfinance, pandas, matplotlib
"""
import json
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
    # additional tickers for comparison & SGOV yield
    qqq = yf.download('QQQ', period='1y', progress=False, auto_adjust=True)['Close'].squeeze().dropna()
    spy = yf.download('SPY', period='1y', progress=False, auto_adjust=True)['Close'].squeeze().dropna()
    sgov = yf.download('SGOV', period='1y', progress=False, auto_adjust=True)['Close'].squeeze().dropna()
    return t, ma200, qqq, spy, sgov

def _period_return(series, days):
    """Calculate return over last N trading days."""
    if len(series) < days + 1:
        return None
    return round((float(series.iloc[-1]) / float(series.iloc[-days - 1]) - 1) * 100, 2)

def _classify(price, ma, envelope):
    if price < ma:
        return "하락"
    elif price < envelope:
        return "집중투자"
    else:
        return "과열"

def build_signal_history(t, ma200):
    """Find last 5 state transitions with P&L on TQQQ exits."""
    env = ma200 * 1.05
    valid = t.index[ma200.notna()]
    if len(valid) < 2:
        return []
    prev_state = _classify(float(t[valid[0]]), float(ma200[valid[0]]), float(env[valid[0]]))
    transitions = []
    entry_price = None  # price when entering TQQQ (하락→집중투자 or 하락→과열)
    for d in valid[1:]:
        cur_state = _classify(float(t[d]), float(ma200[d]), float(env[d]))
        if cur_state != prev_state:
            price = round(float(t[d]), 2)
            pnl = None
            if prev_state == "하락" and cur_state in ("집중투자", "과열"):
                # entering TQQQ
                entry_price = price
            elif prev_state in ("집중투자", "과열") and cur_state == "하락":
                # exiting TQQQ
                if entry_price is not None:
                    pnl = round((price / entry_price - 1) * 100, 2)
                entry_price = None
            transitions.append({
                "date": d.strftime('%Y-%m-%d'),
                "from": prev_state,
                "to": cur_state,
                "price": price,
                "pnl": pnl,
            })
        prev_state = cur_state
    return transitions[-5:]

def build_state(t, ma200, qqq, spy, sgov):
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

    # drawdown from 52-week high
    drawdown = round((price / high52 - 1) * 100, 2)

    # SGOV yield estimate (annualized from 1-month return)
    sgov_1m_ret = _period_return(sgov, 22)
    sgov_yield = round(sgov_1m_ret * 12, 2) if sgov_1m_ret is not None else None

    # comparison returns
    compare = {}
    for name, series in [("TQQQ", t), ("QQQ", qqq), ("SPY", spy)]:
        compare[name] = {
            "1w": _period_return(series, 5),
            "1m": _period_return(series, 22),
            "3m": _period_return(series, 66),
        }

    # signal history
    signals = build_signal_history(t, ma200)

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
        "drawdown": drawdown,
        "sgov_yield": sgov_yield,
        "compare": compare,
        "signals": signals,
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

def _fmt_ret(v):
    """Format return value with sign, or '-' if None."""
    if v is None:
        return "-"
    return f"{v:+.2f}%"

def build_section(s):
    # signal history table
    sig_rows = ""
    state_emoji = {"하락": "🟦", "집중투자": "🟥", "과열": "🟧"}
    for sig in s.get("signals", []):
        f_em = state_emoji.get(sig['from'], '')
        t_em = state_emoji.get(sig['to'], '')
        pnl = sig.get('pnl')
        if pnl is not None:
            pnl_str = f"**{pnl:+.2f}%**" if pnl >= 0 else f"**{pnl:+.2f}%**"
        else:
            pnl_str = "-"
        sig_rows += f"| {sig['date']} | {f_em} {sig['from']} → {t_em} {sig['to']} | ${sig['price']} | {pnl_str} |\n"
    if not sig_rows:
        sig_rows = "| - | 전환 이력 없음 | - | - |\n"

    # comparison table
    c = s.get("compare", {})
    comp_rows = ""
    for name in ["TQQQ", "QQQ", "SPY"]:
        r = c.get(name, {})
        comp_rows += f"| **{name}** | {_fmt_ret(r.get('1w'))} | {_fmt_ret(r.get('1m'))} | {_fmt_ret(r.get('3m'))} |\n"

    # SGOV yield
    sgov_line = f"{s['sgov_yield']:.2f}% (추정)" if s.get('sgov_yield') is not None else "N/A"

    # drawdown
    dd = s.get('drawdown', 0)
    dd_bar_pct = min(abs(dd), 100)
    if abs(dd) < 10:
        dd_color = "🟢"
    elif abs(dd) < 30:
        dd_color = "🟡"
    else:
        dd_color = "🔴"

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

### 📈 주요 수치

| 항목 | 값 |
|---|---:|
| **TQQQ 종가** | ${s['price']} |
| **200일 이동평균선** | ${s['ma200']} |
| **과열선 (200MA +5%)** | ${s['envelope']} |
| **200일선 대비 괴리** | **{s['diff_pct']:+.2f}%** {s['diff_emoji']} |
| **52주 최고가** | ${s['high52']} |
| **52주 최저가** | ${s['low52']} |
| **SGOV 예상 수익률** | {sgov_line} |

### 📉 드로다운 현황

{dd_color} 52주 최고 대비 **{dd:+.2f}%** (${s['high52']} → ${s['price']})

### 🔄 수익률 비교

| 종목 | 1주 | 1개월 | 3개월 |
|---|---:|---:|---:|
{comp_rows}
### 🔀 최근 시그널 전환 이력

| 날짜 | 전환 | TQQQ 가격 | 손익 |
|---|---|---:|---:|
{sig_rows}
### 🛒 주문하기

<Card title="토스증권에서 TQQQ 주문" icon="cart-shopping" href="https://www.tossinvest.com/stocks/US20100211003/order">
  현재 신호에 맞춰 바로 주문 페이지로 이동
</Card>

{{/* TOSS_POSTS_START */}}
{{/* TOSS_POSTS_END */}}

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
        f"• 52주 고/저: ${s['high52']} / ${s['low52']}"
    )
    reply_markup = {
        "inline_keyboard": [[
            {"text": "📊 대시보드", "url": "https://hooniis.mintlify.app/dashboard"},
            {"text": "🛒 주문하기", "url": "https://www.tossinvest.com/stocks/US20100211003/order"},
        ]]
    }
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": "true",
        "reply_markup": json.dumps(reply_markup),
    }).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=10) as r:
            print(f"✅ 텔레그램 전송: {r.status}")
    except Exception as e:
        print(f"⚠️ 텔레그램 전송 실패: {e}")

def main():
    t, ma200, qqq, spy, sgov = fetch_data()
    state = build_state(t, ma200, qqq, spy, sgov)
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
