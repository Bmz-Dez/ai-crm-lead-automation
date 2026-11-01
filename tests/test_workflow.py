from unittest.mock import patch
from fastapi.testclient import TestClient
from app import app
from schemas import LeadInput, LeadTriageResult

client = TestClient(app)


def test_health_endpoint():
    """Verify the FastAPI health check responds with 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_missing_email_guardrail_bypasses_llm():
    """Verify missing or invalid emails are caught deterministically without calling Groq."""
    payload = {
        "name": "Jan Nowak",
        "email": "invalid-email-format",
        "company": "Nowak Sp. z o.o.",
        "message": "We want to buy 50 licenses.",
    }
    response = client.post("/api/v1/leads/triage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["triage"]["category"] == "incomplete_data"
    assert data["triage"]["routing_action"] == "human_escalation"
    assert data["crm_execution"]["status"] == "routed_to_human_queue"
    assert data["crm_execution"]["synced"] is False


@patch("app.triage_lead")
def test_hot_lead_auto_syncs_to_hubspot(mock_triage):
    """Verify a qualified hot lead triggers the HubSpot CRM sync payload."""
    mock_triage.return_value = LeadTriageResult(
        category="hot_lead",
        lead_score=95,
        sentiment="positive",
        routing_action="auto_sync_crm",
        reasoning="Enterprise migration request with clear timeline.",
        draft_reply="Hi Anna, let's schedule your demo.",
    )

    payload = {
        "name": "Anna Kowalska",
        "email": "anna@enterprise.pl",
        "company": "PolTech SA",
        "message": "Need 200 CRM seats next month.",
    }
    response = client.post("/api/v1/leads/triage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["crm_execution"]["synced"] is True
    assert data["crm_execution"]["crm_provider"] == "HubSpot_v3"
    props = data["crm_execution"]["payload_sent"]["properties"]
    assert props["email"] == "anna@enterprise.pl"
    assert props["firstname"] == "Anna"
    assert props["lastname"] == "Kowalska"
    assert props["hs_lead_status"] == "NEW"


@patch("app.triage_lead")
def test_angry_customer_routes_to_human_queue(mock_triage):
    """Verify angry customers are never auto-synced and always escalate to a human."""
    mock_triage.return_value = LeadTriageResult(
        category="angry_customer",
        lead_score=90,
        sentiment="negative",
        routing_action="human_escalation",
        reasoning="Customer reporting critical outage.",
        draft_reply="We are escalating your issue immediately.",
    )

    payload = {
        "name": "Marek Zielinski",
        "email": "marek@client.pl",
        "company": "Client Corp",
        "message": "System is down! Fix it now!",
    }
    response = client.post("/api/v1/leads/triage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["crm_execution"]["status"] == "routed_to_human_queue"
    assert data["crm_execution"]["synced"] is False


@patch("app.triage_lead")
def test_spam_lead_is_discarded(mock_triage):
    """Verify spam leads are filtered out before polluting the CRM database."""
    mock_triage.return_value = LeadTriageResult(
        category="spam",
        lead_score=0,
        sentiment="neutral",
        routing_action="discard_spam",
        reasoning="Unsolicited crypto promotion.",
        draft_reply="N/A - Spam discarded",
    )

    payload = {
        "name": "Crypto Winner",
        "email": "promo@spammer.xyz",
        "message": "Buy 100x token now free airdrop!",
    }
    response = client.post("/api/v1/leads/triage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["crm_execution"]["status"] == "spam_discarded"
    assert data["crm_execution"]["synced"] is False