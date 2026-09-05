# AI Ticket Triage Tool

Reads support tickets, generates a one-line summary, assigns a category,
and scores priority 1-5 — automatically. Built to demonstrate the
resume line:



## Architecture

```
tickets_raw.csv  (stand-in for a helpdesk export / S3 landing zone)
        |
        v
  generate_sample_data.py   ->  tickets_raw.csv
        |
        v
  triage.py  --------------------------------
        |  if ANTHROPIC_API_KEY set:         |
        |    -> calls Claude API per ticket  |  LIVE mode
        |    -> summary + category + score   |
        |  else:                             |
        |    -> rule-based heuristic scorer  |  FREE fallback mode
        -------------------------------------
        |
        v
    tickets.db  (SQLite)
        |
        v
  report.py       -> report.md, results.csv
  dashboard.py    -> dashboard.html
```

In a production version, `tickets_raw.csv` would instead be a daily
export from Zendesk/Freshdesk/Intercom landing in an **S3** bucket,
picked up by a scheduled Lambda or cron job that runs `triage.py`
and writes to a real **SQL** database (Postgres/RDS instead of SQLite).
The pipeline logic itself doesn't change — only where the data comes
from and where it's stored.




## How to run it

```bash
pip install anthropic          # only needed for live mode
python3 generate_sample_data.py   # creates tickets_raw.csv (400 synthetic tickets)
python3 triage.py                 # scores every ticket -> tickets.db
python3 report.py                 # -> report.md, results.csv
python3 dashboard.py              # -> dashboard.html (open in a browser)
```

To use the real Claude API instead of the free fallback:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python3 triage.py
python3 dashboard.py
```

## Results 

- **62% estimated reduction** in review time (4 min/ticket manual vs
  1.5 min/ticket to confirm an AI-scored ticket) — this is where the
  resume's "60%" figure comes from; it's a real calculation, not a
  guess, and you can defend the assumptions if asked.
- 77 tickets flagged priority 5 (critical) out of 400, surfaced at the
  top of the queue instead of buried in arrival order.
- Full category and priority breakdown in `report.md` / `dashboard.html`.

## Sumamry

- **What it does**: ingests unstructured ticket text, uses an LLM to
  extract structured signal (category + urgency) that isn't in the
  raw data, and turns "10,000 tickets in arrival order" into "77
  things to look at right now."

- **Why the fallback mode matters**: shows you designed for graceful
  degradation and cost control, not just "call the API and hope" —
  a real production concern once you're processing 10,000+ tickets/month.
- **The 60% number**: walk through the assumption (4 min manual vs
  1.5 min AI-assisted) rather than presenting it as a measured fact
  from a real deployment, since this is demo data. Interviewers respect
  "here's how I'd validate this against real data" more than an
  unexplained stat.

## Scaling this to 10,000+/month for real

1. Swap SQLite for Postgres (RDS) — schema is already there in `triage.py`.
2. Add a batch/async wrapper using the Claude API's Message Batches
   endpoint to cut cost when processing thousands of tickets at once.
3. Add a `processed` flag so re-runs only score new tickets, not the
   whole history.
4. Point `tickets_raw.csv` at S3 and trigger the pipeline on new-file
   events (S3 -> Lambda) or a nightly scheduled job.
