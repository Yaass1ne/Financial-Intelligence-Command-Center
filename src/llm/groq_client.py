"""
FINCENTER Groq LLM Client

Provides natural language Q&A over financial data using
the Groq API with Llama-3.3-70B-Versatile model.
"""

from groq import Groq
from src.config import settings

_client: Groq | None = None


def get_client() -> Groq:
    """Return a shared Groq client (lazy singleton)."""
    global _client
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


def build_system_prompt(context: str) -> str:
    return f"""You are FINCENTER's financial intelligence assistant.
You answer questions about invoices, contracts, budgets, and financial analytics
based exclusively on the data provided in the context below.

Rules:
- Be concise and factual.
- Format numbers with commas and currency symbols where appropriate.
- If the answer is not in the context, say "I don't have enough data to answer that."
- Never make up figures.

--- FINANCIAL DATA CONTEXT ---
{context}
--- END CONTEXT ---"""


def answer_question(question: str, context: str) -> str:
    """
    Send a question + financial context to Groq and return the answer.

    Args:
        question: The user's natural language question.
        context:  Relevant financial data as a formatted string.

    Returns:
        The model's answer as a plain string.
    """
    client = get_client()
    completion = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": build_system_prompt(context)},
            {"role": "user", "content": question},
        ],
        max_tokens=settings.GROQ_MAX_TOKENS,
        temperature=0.2,
    )
    return completion.choices[0].message.content
