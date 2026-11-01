from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from config import settings
from schemas import LeadInput, LeadTriageResult

SYSTEM_PROMPT = """You are an enterprise CRM Lead-Triage AI Agent.
Analyze the incoming lead message and classify it accurately for our CRM workflow:

1. Category rules:
   - 'hot_lead': Clear budget, timeline, or enterprise buying intent (score 75-100).
   - 'warm_lead': General product interest or pricing inquiry (score 40-74).
   - 'cold_lead': Vague inquiry or low fit (score 10-39).
   - 'angry_customer': Existing customer complaining, demanding a refund, or reporting an outage (score 80-100 for urgency).
   - 'spam': Promotional junk, SEO pitches, crypto scams, or gibberish (score 0).

2. Routing rules:
   - 'auto_sync_crm': For hot_lead, warm_lead, or cold_lead with valid contact details.
   - 'human_escalation': MUST be used for 'angry_customer' or ambiguous/high-risk enterprise requests.
   - 'discard_spam': MUST be used for 'spam'.

3. Draft Reply:
   - Write a concise, professional reply matching the sender's need.
   - For spam, set draft_reply to 'N/A - Spam discarded'.
"""


def triage_lead(lead: LeadInput) -> LeadTriageResult:
    """Evaluates an incoming lead using deterministic guardrails + Groq structured LLM output."""
    # 1. Deterministic guardrail: catch missing or invalid email before calling the LLM
    if not lead.has_valid_email():
        return LeadTriageResult(
            category="incomplete_data",
            lead_score=20,
            sentiment="neutral",
            routing_action="human_escalation",
            reasoning="Lead is missing a valid email address; routed to human review for manual lookup.",
            draft_reply="N/A - Missing valid email address. Flagged for manual review.",
        )

    # 2. LLM structured triage via Groq
    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.0,
    )
    structured_llm = llm.with_structured_output(LeadTriageResult)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        (
            "human",
            "Lead Name: {name}\nEmail: {email}\nCompany: {company}\nMessage: {message}",
        ),
    ])

    chain = prompt | structured_llm
    result: LeadTriageResult = chain.invoke({
        "name": lead.name,
        "email": lead.email,
        "company": lead.company or "Not provided",
        "message": lead.message,
    })

    # 3. Post-LLM business rule guardrail: never auto-reply to an angry customer or spam
    if result.category == "angry_customer":
        result.routing_action = "human_escalation"
    elif result.category == "spam":
        result.routing_action = "discard_spam"
        result.lead_score = 0

    return result