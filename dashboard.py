"""
dashboard.py
------------
Builds a single self-contained HTML dashboard (dashboard.html) from
tickets.db - the kind of thing you'd screenshot for a portfolio or
show live in an interview.
"""

import sqlite3
import json

DB_PATH = "tickets.db"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Ticket Triage Dashboard</title>
<style>
  :root {{
    --ink: #1c2321;
    --paper: #f6f5f1;
    --line: #d8d4c8;
    --signal: #b5482a;
    --muted: #6b6a63;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font-family: 'Iowan Old Style', 'Georgia', serif;
    padding: 48px 32px;
  }}
  .wrap {{ max-width: 980px; margin: 0 auto; }}
  h1 {{
    font-size: 30px;
    margin: 0 0 4px;
    font-weight: 600;
    letter-spacing: -0.01em;
  }}
  .sub {{ color: var(--muted); font-size: 15px; margin-bottom: 36px; }}
  .stats {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: var(--line);
    border: 1px solid var(--line);
    margin-bottom: 40px;
  }}
  .stat {{ background: var(--paper); padding: 20px 18px; }}
  .stat .num {{ font-size: 32px; font-weight: 600; line-height: 1; }}
  .stat .label {{ color: var(--muted); font-size: 13px; margin-top: 6px; font-family: -apple-system, sans-serif; }}
  .stat.hi .num {{ color: var(--signal); }}
  section {{ margin-bottom: 40px; }}
  h2 {{
    font-family: -apple-system, sans-serif;
    font-size: 13px;
    text-transform: none;
    color: var(--muted);
    border-bottom: 1px solid var(--line);
    padding-bottom: 8px;
    margin-bottom: 16px;
    font-weight: 600;
  }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th {{
    text-align: left;
    font-family: -apple-system, sans-serif;
    font-weight: 600;
    color: var(--muted);
    font-size: 12px;
    padding: 6px 10px 6px 0;
    border-bottom: 1px solid var(--line);
  }}
  td {{ padding: 9px 10px 9px 0; border-bottom: 1px solid var(--line); vertical-align: top; }}
  .prio {{
    display: inline-block;
    min-width: 20px;
    text-align: center;
    font-family: -apple-system, sans-serif;
    font-weight: 700;
    font-size: 12px;
    padding: 2px 6px;
    border-radius: 3px;
  }}
  .p5 {{ background: #f0d9d3; color: #8a2e17; }}
  .p4 {{ background: #f5e6d3; color: #8a5a17; }}
  .p3 {{ background: #eef0e5; color: #55611f; }}
  .p2, .p1 {{ background: #e7e6e0; color: var(--muted); }}
  .bar-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 10px; font-family: -apple-system, sans-serif; font-size: 13px;}}
  .bar-label {{ width: 130px; flex-shrink: 0; color: var(--ink); }}
  .bar-track {{ flex: 1; background: var(--line); height: 14px; position: relative; }}
  .bar-fill {{ background: var(--signal); height: 100%; opacity: 0.75; }}
  .bar-count {{ width: 40px; text-align: right; color: var(--muted); flex-shrink: 0; }}
  footer {{ color: var(--muted); font-size: 12px; font-family: -apple-system, sans-serif; margin-top: 40px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>AI Ticket Triage &mdash; Results</h1>
  <div class="sub">{total} tickets processed &middot; mode: {mode}</div>

  <div class="stats">
    <div class="stat hi"><div class="num">{saved_pct}%</div><div class="label">Est. review time saved</div></div>
    <div class="stat"><div class="num">{critical_count}</div><div class="label">Critical (priority 5)</div></div>
    <div class="stat"><div class="num">{manual_hours}h</div><div class="label">Manual review time</div></div>
    <div class="stat"><div class="num">{ai_hours}h</div><div class="label">AI-assisted review time</div></div>
  </div>

  <section>
    <h2>Volume by category</h2>
    {category_bars}
  </section>

  <section>
    <h2>Top priority tickets</h2>
    <table>
      <tr><th>ID</th><th>Priority</th><th>Category</th><th>Customer</th><th>Summary</th></tr>
      {ticket_rows}
    </table>
  </section>

  <footer>Generated from tickets.db by dashboard.py &middot; synthetic demo data</footer>
</div>
</body>
</html>
"""


def bar_row(label, count, max_count):
    pct = int((count / max_count) * 100) if max_count else 0
    return f"""<div class="bar-row">
      <div class="bar-label">{label}</div>
      <div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>
      <div class="bar-count">{count}</div>
    </div>"""


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(*) c FROM tickets").fetchone()["c"]
    critical_count = cur.execute(
        "SELECT COUNT(*) c FROM tickets WHERE priority_score = 5"
    ).fetchone()["c"]

    manual_min = total * 4
    ai_min = total * 1.5
    saved_pct = round((manual_min - ai_min) / manual_min * 100)

    by_category = cur.execute(
        "SELECT category, COUNT(*) c FROM tickets GROUP BY category ORDER BY c DESC"
    ).fetchall()
    max_cat = max(r["c"] for r in by_category)
    category_bars = "\n".join(bar_row(r["category"], r["c"], max_cat) for r in by_category)

    top = cur.execute(
        """SELECT ticket_id, customer, category, priority_score, summary
           FROM tickets ORDER BY priority_score DESC, ticket_id ASC LIMIT 15"""
    ).fetchall()
    ticket_rows = "\n".join(
        f"""<tr>
          <td>{r['ticket_id']}</td>
          <td><span class="prio p{r['priority_score']}">{r['priority_score']}</span></td>
          <td>{r['category']}</td>
          <td>{r['customer']}</td>
          <td>{r['summary']}</td>
        </tr>"""
        for r in top
    )

    mode = "mock/free (no API key set)" if True else "live"
    import os
    mode = "live (Claude API)" if os.environ.get("ANTHROPIC_API_KEY") else "free rule-based fallback"

    html = HTML_TEMPLATE.format(
        total=total,
        mode=mode,
        saved_pct=saved_pct,
        critical_count=critical_count,
        manual_hours=round(manual_min / 60, 1),
        ai_hours=round(ai_min / 60, 1),
        category_bars=category_bars,
        ticket_rows=ticket_rows,
    )

    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote dashboard.html")


if __name__ == "__main__":
    main()
