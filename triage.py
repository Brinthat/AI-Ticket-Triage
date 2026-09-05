"""
triage.py
---------
Reads raw support tickets, summarizes + scores each one, and writes
results into a SQLite database.

Two modes, chosen automatically:
  1. LIVE  - if ANTHROPIC_API_KEY is set, calls the Claude API to produce
             a real summary, category, and 1-5 priority score per ticket.
  2. MOCK  - if no key is set, uses a fast rule-based heuristic scorer so
             the whole pipeline still runs end-to-end for free, with no
             account needed. Same schema, same downstream report.

Usage:
    python triage.py                # mock mode (free, no key needed)
    ANTHROPIC_API_KEY=sk-... python triage.py   # live mode via Claude API
"""

import csv
import json
import os
import re
import sqlite3
import time

DB_PATH = "tickets.db"
INPUT_CSV = "tickets_raw.csv"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id INTEGER PRIMARY KEY,
    created_at TEXT,
    customer TEXT,
    channel TEXT,
    subject TEXT,
    body TEXT,
    summary TEXT,
    category TEXT,
    priority_score INTEGER,   -- 1 (low) to 5 (critical)
    priority_reason TEXT,
    processed_at TEXT
);
"""

CATEGORIES = [
    "billing", "technical", "account", "bug", "feature_request",
    "onboarding", "cancellation", "praise", "security", "other",
]

URGENT_WORDS = [
    "urgent", "immediately", "asap", "outage", "down", "critical",
    "compromised", "data loss", "locked out", "not working", "failing",
    "right now", "overnight", "cancel",
]


# --------------------------------------------------------------------------
# MOCK scorer - zero cost, zero API key, deterministic. This is what lets
# the whole pipeline be demoed for free in the 2-hour build.
# --------------------------------------------------------------------------
def mock_triage(subject: str, body: str) -> dict:
    text = f"{subject} {body}".lower()

    category = "other"
    for cat in CATEGORIES:
        if cat.replace("_", " ") in text or cat in text:
            category = cat
            break
    if "cancel" in text:
        category = "cancellation"
    elif "refund" in text or "charge" in text or "invoice" in text or "billed" in text:
        category = "billing"
    elif "login" in text or "locked" in text or "password" in text:
        category = "account"
    elif "api" in text or "webhook" in text or "sync" in text or "error" in text:
        category = "technical"

    hits = sum(1 for w in URGENT_WORDS if w in text)
    if "compromised" in text or "data loss" in text or "outage" in text:
        score = 5
    elif hits >= 2:
        score = 4
    elif hits == 1:
        score = 3
    elif "thanks" in text or "thank you" in text or "not urgent" in text or "no rush" in text:
        score = 1
    else:
        score = 2

    first_sentence = re.split(r"(?<=[.!?])\s", body.strip())[0]
    summary = f"{subject}: {first_sentence}"

    return {
        "summary": summary,
        "category": category,
        "priority_score": score,
        "priority_reason": f"heuristic match: {hits} urgency keyword(s) found",
    }


# --------------------------------------------------------------------------
# LIVE scorer - real Claude API call. Requires ANTHROPIC_API_KEY.
# --------------------------------------------------------------------------
def live_triage(subject: str, body: str, client, model="claude-sonnet-4-6") -> dict:
    prompt = f"""You are triaging a customer support ticket.

Subject: {subject}
Body: {body}

Return ONLY valid JSON, no other text, in this exact shape:
{{"summary": "one sentence summary", "category": "one of {CATEGORIES}", "priority_score": <int 1-5, 5=critical>, "priority_reason": "short justification"}}"""

    resp = client.messages.create(
        model=model,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip()
    raw = re.sub(r"^```json|```$", "", raw).strip()
    return json.loads(raw)


def get_client_if_available():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        print("anthropic package not installed (pip install anthropic). Falling back to mock mode.")
        return None


def main():
    client = get_client_if_available()
    mode = "LIVE (Claude API)" if client else "MOCK (free, rule-based fallback)"
    print(f"Running in {mode} mode.\n")

    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    conn.commit()

    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    t0 = time.time()
    processed = 0
    for row in rows:
        if client:
            try:
                result = live_triage(row["subject"], row["body"], client)
            except Exception as e:
                print(f"  [warn] ticket {row['ticket_id']} API call failed ({e}), using mock fallback")
                result = mock_triage(row["subject"], row["body"])
        else:
            result = mock_triage(row["subject"], row["body"])

        conn.execute(
            """INSERT OR REPLACE INTO tickets
               (ticket_id, created_at, customer, channel, subject, body,
                summary, category, priority_score, priority_reason, processed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                row["ticket_id"], row["created_at"], row["customer"], row["channel"],
                row["subject"], row["body"], result["summary"], result["category"],
                result["priority_score"], result["priority_reason"],
            ),
        )
        processed += 1
        if processed % 100 == 0:
            print(f"  processed {processed}/{len(rows)}")

    conn.commit()
    conn.close()
    elapsed = time.time() - t0
    print(f"\nDone. {processed} tickets processed in {elapsed:.1f}s -> {DB_PATH}")


if __name__ == "__main__":
    main()
