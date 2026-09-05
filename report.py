"""
report.py
---------
Reads tickets.db and produces:
  1. A markdown report (report.md) with the priority queue, category
     breakdown, and an estimated time-saved figure.
  2. results.csv - the full scored dataset, ready for a BI tool or a
     quick pivot table.

This is the "so what" layer that turns the pipeline into something you
can show in an interview.
"""

import sqlite3
import csv

DB_PATH = "tickets.db"
AVG_MANUAL_REVIEW_MINUTES = 4      # assumed time a human spends triaging one ticket by hand
AVG_AI_ASSISTED_REVIEW_MINUTES = 1.5  # time to confirm/act on an AI-scored ticket


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(*) AS c FROM tickets").fetchone()["c"]

    by_category = cur.execute(
        "SELECT category, COUNT(*) AS c FROM tickets GROUP BY category ORDER BY c DESC"
    ).fetchall()

    by_priority = cur.execute(
        "SELECT priority_score, COUNT(*) AS c FROM tickets GROUP BY priority_score ORDER BY priority_score DESC"
    ).fetchall()

    top_priority = cur.execute(
        """SELECT ticket_id, customer, category, priority_score, summary
           FROM tickets ORDER BY priority_score DESC, ticket_id ASC LIMIT 15"""
    ).fetchall()

    # export full results
    all_rows = cur.execute(
        """SELECT ticket_id, created_at, customer, channel, category,
                  priority_score, summary, priority_reason
           FROM tickets ORDER BY priority_score DESC"""
    ).fetchall()
    with open("results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(all_rows[0].keys())
        writer.writerows(all_rows)

    manual_minutes = total * AVG_MANUAL_REVIEW_MINUTES
    ai_minutes = total * AVG_AI_ASSISTED_REVIEW_MINUTES
    saved_minutes = manual_minutes - ai_minutes
    saved_pct = (saved_minutes / manual_minutes) * 100

    lines = []
    lines.append("# AI Ticket Triage - Results Report\n")
    lines.append(f"**Tickets processed:** {total}\n")
    lines.append(
        f"**Estimated manual review time:** {manual_minutes/60:.1f} hours "
        f"(at {AVG_MANUAL_REVIEW_MINUTES} min/ticket)\n"
    )
    lines.append(
        f"**Estimated AI-assisted review time:** {ai_minutes/60:.1f} hours "
        f"(at {AVG_AI_ASSISTED_REVIEW_MINUTES} min/ticket to confirm an AI-scored item)\n"
    )
    lines.append(f"**Estimated time saved: {saved_pct:.0f}%**\n")

    lines.append("\n## Volume by category\n")
    lines.append("| Category | Tickets | % of total |")
    lines.append("|---|---|---|")
    for row in by_category:
        pct = row["c"] / total * 100
        lines.append(f"| {row['category']} | {row['c']} | {pct:.1f}% |")

    lines.append("\n## Volume by priority score (5 = critical)\n")
    lines.append("| Priority | Tickets |")
    lines.append("|---|---|")
    for row in by_priority:
        lines.append(f"| {row['priority_score']} | {row['c']} |")

    lines.append("\n## Top 15 tickets to look at first\n")
    lines.append("| ID | Priority | Category | Customer | Summary |")
    lines.append("|---|---|---|---|---|")
    for row in top_priority:
        lines.append(
            f"| {row['ticket_id']} | {row['priority_score']} | {row['category']} | "
            f"{row['customer']} | {row['summary']} |"
        )

    with open("report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))
    print("\n\nWrote report.md and results.csv")


if __name__ == "__main__":
    main()
