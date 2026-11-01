from typing import Any, Dict
import requests
from config import settings
from schemas import LeadInput, LeadTriageResult

HUBSPOT_CONTACTS_URL = "https://api.hubapi.com/crm/v3/objects/contacts"


def sync_lead_to_hubspot(lead: LeadInput, triage: LeadTriageResult) -> Dict[str, Any]:
    """
    Creates or updates a contact in HubSpot CRM via REST API v3.
    Supports a safe dry-run mode for local development and CI testing.
    """
    # Split full name into firstname / lastname for HubSpot standard properties
    name_parts = lead.name.strip().split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    payload = {
        "properties": {
            "email": lead.email,
            "firstname": first_name,
            "lastname": last_name,
            "company": lead.company or "",
            "hs_lead_status": "NEW" if triage.category == "hot_lead" else "OPEN",
            "jobtitle": f"AI Score: {triage.lead_score} ({triage.category})",
        }
    }

    # Safe Dry-Run Mode (default when testing or running in CI without HubSpot credentials)
    if settings.crm_dry_run or not settings.hubspot_api_key:
        return {
            "status": "dry_run_success",
            "crm_provider": "HubSpot_v3",
            "synced": True,
            "payload_sent": payload,
        }

    # Live HubSpot REST API Call
    headers = {
        "Authorization": f"Bearer {settings.hubspot_api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        HUBSPOT_CONTACTS_URL,
        json=payload,
        headers=headers,
        timeout=10,
    )

    if response.status_code in (200, 201):
        return {
            "status": "live_sync_success",
            "crm_provider": "HubSpot_v3",
            "synced": True,
            "hubspot_id": response.json().get("id"),
        }

    return {
        "status": "crm_api_error",
        "crm_provider": "HubSpot_v3",
        "synced": False,
        "http_status": response.status_code,
        "detail": response.text,
    }