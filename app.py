from typing import Any, Dict
from fastapi import FastAPI
from agent import triage_lead
from crm_client import sync_lead_to_hubspot
from schemas import LeadInput, LeadTriageResult

app = FastAPI(
    title="AI CRM Lead-Triage & Automation Service",
    description="Webhook microservice for n8n and Creatio low-code CRM workflows.",
    version="1.0.0",
)


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint for Docker, CI pipelines, and n8n/Creatio monitoring."""
    return {"status": "healthy", "service": "ai-crm-lead-automation"}


@app.post("/api/v1/leads/triage")
def process_lead_workflow(lead: LeadInput) -> Dict[str, Any]:
    """
    Main BPMN workflow endpoint:
    1. Triages and scores the incoming lead using guardrails + Groq LLM.
    2. Executes deterministic routing (CRM auto-sync, human escalation, or spam discard).
    """
    triage_result: LeadTriageResult = triage_lead(lead)

    if triage_result.routing_action == "auto_sync_crm":
        crm_status = sync_lead_to_hubspot(lead, triage_result)
    elif triage_result.routing_action == "human_escalation":
        crm_status = {
            "status": "routed_to_human_queue",
            "synced": False,
            "reason": triage_result.reasoning,
        }
    else:
        crm_status = {
            "status": "spam_discarded",
            "synced": False,
            "reason": "Filtered out before reaching CRM database.",
        }

    return {
        "lead_input": lead.model_dump(),
        "triage": triage_result.model_dump(),
        "crm_execution": crm_status,
    }