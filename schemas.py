from typing import Literal, Optional
from pydantic import BaseModel, Field


class LeadInput(BaseModel):
    """Incoming lead payload from a web form, email webhook, or Creatio/n8n node."""
    name: str = Field(default="Unknown", description="Full name of the lead")
    email: Optional[str] = Field(default=None, description="Email address of the lead")
    company: Optional[str] = Field(default=None, description="Company or organization name")
    message: str = Field(..., description="Raw message or inquiry from the lead")

    def has_valid_email(self) -> bool:
        """Deterministic check before calling the LLM to catch missing or malformed emails."""
        if not self.email or "@" not in self.email or "." not in self.email.split("@")[-1]:
            return False
        return True


class LeadTriageResult(BaseModel):
    """Structured output contract returned by the LLM triage agent."""
    category: Literal[
        "hot_lead",
        "warm_lead",
        "cold_lead",
        "angry_customer",
        "spam",
        "incomplete_data",
    ] = Field(description="Classification of the incoming message")
    lead_score: int = Field(
        ge=0,
        le=100,
        description="Priority score from 0 to 100 based on buying intent and urgency",
    )
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        description="Detected emotional tone of the sender"
    )
    routing_action: Literal["auto_sync_crm", "human_escalation", "discard_spam"] = Field(
        description="Next step in the BPMN business process workflow"
    )
    reasoning: str = Field(
        description="Brief 1-sentence explanation for the score and routing decision"
    )
    draft_reply: str = Field(
        description="Polite, context-aware email draft ready to send or for human review"
    )