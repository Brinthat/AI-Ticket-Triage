"""
generate_sample_data.py
------------------------
Creates a synthetic support-ticket dataset so the pipeline can be demoed
without needing access to a real helpdesk export (Zendesk, Freshdesk, etc.).

In production this step is replaced by a scheduled export/API pull from
your real ticketing system landing in S3 (see README.md).
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)  # reproducible demo data

CUSTOMERS = [
    "Priya Shah", "Marcus Lee", "Fatima Noor", "Tom Becker", "Ana Souza",
    "Wei Zhang", "Liam O'Brien", "Sara Kim", "Diego Torres", "Grace Adeyemi",
    "Noah Fischer", "Elena Petrova", "Ravi Kumar", "Chloe Martin", "Sam Osei",
]

CHANNELS = ["email", "chat", "web_form", "phone_transcript"]

# (category, true_urgency_hint, subject, body_template)
TEMPLATES = [
    ("billing", "high", "Charged twice this month",
     "I was billed twice for my subscription on {date}. Please refund the "
     "duplicate charge of ${amt} as soon as possible, this is affecting my "
     "small business account."),
    ("billing", "low", "Question about invoice format",
     "Is it possible to get invoices with our VAT number included? Not "
     "urgent, just tidying up our accounting records."),
    ("technical", "critical", "Production outage - API returning 500s",
     "Our integration has been down for the last 40 minutes, every request "
     "to your API is returning 500 errors. This is impacting our live "
     "customers right now, we need help immediately."),
    ("technical", "medium", "Intermittent sync errors",
     "We're seeing occasional sync failures between your app and our CRM, "
     "maybe 1 in 20 records. Log excerpt attached. Not blocking us yet but "
     "would like it looked at."),
    ("account", "high", "Locked out of admin account",
     "I can't log into the admin console since this morning, it says my "
     "account is locked. I need access today to run payroll approvals."),
    ("account", "low", "How do I add a teammate?",
     "New hire starting next week, what's the process for adding them as a "
     "seat on our plan?"),
    ("feature_request", "low", "Dark mode request",
     "Would love a dark mode option for the dashboard, easier on the eyes "
     "during night shifts. No rush at all."),
    ("bug", "medium", "Export button does nothing",
     "Clicking 'Export to CSV' on the reports page just spins forever, "
     "tried in Chrome and Firefox. Happens every time on the monthly view."),
    ("bug", "critical", "Data loss after update",
     "After the latest app update this morning, all of our saved templates "
     "disappeared. We need these restored urgently, they're used daily."),
    ("onboarding", "medium", "Trouble importing contacts",
     "Following the setup guide but our CSV import keeps failing at row "
     "12, no clear error message shown."),
    ("cancellation", "high", "Want to cancel subscription",
     "We'd like to cancel our plan effective end of month, please confirm "
     "the process and whether we get a partial refund."),
    ("praise", "low", "Just wanted to say thanks",
     "Your support team helped us out last week and it was fantastic, "
     "wanted to pass along our thanks."),
    ("security", "critical", "Suspicious login attempts",
     "We're seeing repeated failed login attempts from unfamiliar IP "
     "addresses on our account overnight. Can you check if we've been "
     "compromised?"),
    ("technical", "high", "Webhook deliveries failing",
     "Our webhook endpoint hasn't received any events since yesterday "
     "afternoon, but your status page shows all green. Orders are piling "
     "up unprocessed on our end."),
    ("billing", "medium", "Unexpected plan upgrade charge",
     "We were auto-upgraded to the Pro plan and charged $49 more than "
     "expected, we didn't request this change."),
]

N_TICKETS = 100


def random_date():
    start = datetime(2026, 6, 1)
    return start + timedelta(
        days=random.randint(0, 89),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


def build_ticket(ticket_id: int):
    category, urgency_hint, subject, body_template = random.choice(TEMPLATES)
    created = random_date()
    body = body_template.format(
        date=created.strftime("%b %d"),
        amt=random.choice([9, 19, 29, 49, 99, 149]),
    )
    return {
        "ticket_id": ticket_id,
        "created_at": created.isoformat(timespec="minutes"),
        "customer": random.choice(CUSTOMERS),
        "channel": random.choice(CHANNELS),
        "subject": subject,
        "body": body,
        "true_category_hint": category,       # for later accuracy comparison
        "true_urgency_hint": urgency_hint,     # not shown to the model
    }


def main():
    rows = [build_ticket(i + 1) for i in range(N_TICKETS)]
    fieldnames = list(rows[0].keys())
    with open("tickets_raw.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic tickets to tickets_raw.csv")


if __name__ == "__main__":
    main()
