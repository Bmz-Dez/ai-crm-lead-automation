import sys
from pathlib import Path

# Ensure root project directory is on sys.path when running from evals/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

BENCHMARK_CASES = [
    {
        "name": "Case 1: Enterprise Hot Lead",
        "payload": {
            "name": "Anna Kowalska",
            "email": "anna@poltech.pl",
            "company": "PolTech SA",
            "message": "We want to migrate 200 sales reps to your CRM next month. Can we book a demo this week?",
        },
        "expected_category": "hot_lead",
        "expected_routing": "auto_sync_crm",
        "expected_synced": True,
    },
    {
        "name": "Case 2: General Pricing Inquiry (Warm Lead)",
        "payload": {
            "name": "Piotr Wisniewski",
            "email": "piotr@midmarket.pl",
            "company": "MidMarket Logistics",
            "message": "Hi, could you share your standard pricing tiers for a team of 15 people? Just exploring options for Q3.",
        },
        "expected_category": "warm_lead",
        "expected_routing": "auto_sync_crm",
        "expected_synced": True,
    },
    {
        "name": "Case 3: Angry Customer Escalation",
        "payload": {
            "name": "Marek Zielinski",
            "email": "marek@enterprise-client.pl",
            "company": "Enterprise Client Sp. z o.o.",
            "message": "Your API integration crashed twice today and locked out our billing team! Fix this immediately or we are canceling our contract!",
        },
        "expected_category": "angry_customer",
        "expected_routing": "human_escalation",
        "expected_synced": False,
    },
    {
        "name": "Case 4: Spam / Unsolicited Pitch",
        "payload": {
            "name": "SEO Guru",
            "email": "ranking@backlinks-cheap.xyz",
            "company": "TopRank SEO",
            "message": "CONGRATS! Buy 10,000 backlinks for $29 in Bitcoin and rank #1 on Google overnight! Click here now!",
        },
        "expected_category": "spam",
        "expected_routing": "discard_spam",
        "expected_synced": False,
    },
    {
        "name": "Case 5: Missing Email Edge Case",
        "payload": {
            "name": "Tomasz Krawczyk",
            "email": "",
            "company": "Krawczyk Build",
            "message": "Hello, please call me back regarding a CRM implementation for our construction office.",
        },
        "expected_category": "incomplete_data",
        "expected_routing": "human_escalation",
        "expected_synced": False,
    },
]


def run_evaluation() -> None:
    print("=" * 65)
    print("AI CRM LEAD-TRIAGE BENCHMARK EVALUATION (5 BUSINESS SCENARIOS)")
    print("=" * 65)

    passed = 0
    total = len(BENCHMARK_CASES)

    for case in BENCHMARK_CASES:
        response = client.post("/api/v1/leads/triage", json=case["payload"])
        data = response.json()
        triage = data["triage"]
        crm = data["crm_execution"]

        cat_ok = triage["category"] == case["expected_category"]
        route_ok = triage["routing_action"] == case["expected_routing"]
        sync_ok = crm["synced"] == case["expected_synced"]

        if cat_ok and route_ok and sync_ok:
            passed += 1
            status = "PASS"
        else:
            status = "FAIL"

        print(f"[{status}] {case['name']}")
        print(
            f"       -> Category: {triage['category']} (Score: {triage['lead_score']}) "
            f"| Route: {triage['routing_action']} | CRM Synced: {crm['synced']}"
        )

    print("-" * 65)
    print(f"FINAL EVALUATION SCORE: {passed}/{total} ({(passed / total) * 100:.0f}%)")
    print("=" * 65)


if __name__ == "__main__":
    run_evaluation()