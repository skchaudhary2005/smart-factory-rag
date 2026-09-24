"""Grounded answer generation â€” the LLM layer, built with Pydantic AI.

The retriever (dense + sparse + rerank) is deterministic and lives in `engine.py`; this module is
the *bounded judgement-and-explanation layer* on top of it. The agent answers ONLY from the
retrieved chunks and returns a typed `GroundedAnswer` whose citations are validated against the
chunks that were actually provided â€” so on a factory floor where a wrong answer costs â‚¬50k/hour,
the model cannot cite a page it never saw, and "I don't have enough information" is a first-class,
structured outcome rather than a hallucinated guess.

Model is bound at RUN time, so importing this module needs no API key and tests override the agent
with `TestModel` (`ALLOW_MODEL_REQUESTS=False`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from google.genai import types

from ..config import MODEL


class SourceCitation(BaseModel):
    """A citation grounded by 1-based index into the retrieved chunks."""

    source_id: int = Field(ge=1, description="1-based index into the provided context chunks")
    document: str = ""
    page: int = 0


class GroundedAnswer(BaseModel):
    """Typed answer contract. `insufficient_context` makes 'I don't know' explicit and auditable."""

    answer: str
    citations: list[SourceCitation] = Field(default_factory=list)
    insufficient_context: bool = Field(
        default=False, description="true when the context lacks enough information to answer"
    )
    safety_critical: bool = Field(
        default=False, description="true when the answer involves a safety-critical procedure"
    )
    confidence: float = Field(ge=0.0, le=1.0)


@dataclass
class AnswerDeps:
    """`deps_type` payload: the question + the retrieved chunks the model may cite."""

    question: str
    chunks: list[dict] = field(default_factory=list)


_PERSONA = (
    "You are a manufacturing equipment expert. Answer the question using ONLY the provided context "
    "chunks. Cite every claim by its 1-based [Source N] index and populate `citations` with the ids "
    "you used. If the context does not contain enough information, set insufficient_context=true, "
    "say so plainly, and do not guess. Flag safety_critical=true whenever the answer concerns a "
    "safety-critical procedure, and lead with the safety-relevant information. Respond in the same "
    "language as the question (Greek or English). Set confidence to reflect how directly the context "
    "supports the answer."
)


def _build_model(model):
    if not model.startswith("google:"):
        return model
    model_name = model.split(":", 1)[1]
    client = __import__("google.genai", fromlist=["Client"]).Client(
        api_key=__import__("os").environ.get("GEMINI_API_KEY"),
        http_options=types.HttpOptions(
            timeout=15000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    return GoogleModel(model_name, provider=GoogleProvider(client=client))

answer_agent = Agent(
    deps_type=AnswerDeps,
    output_type=GroundedAnswer,
    instructions=_PERSONA,
    retries=0,
)


@answer_agent.instructions
def _inject_context(ctx: RunContext[AnswerDeps]) -> str:
    chunks = ctx.deps.chunks
    if not chunks:
        return "No context chunks were retrieved. Set insufficient_context=true and cite nothing."
    listing = "\n\n".join(
        f"[Source {i + 1}: {c.get('document', 'unknown')}, p.{c.get('page', 0)}]\n{c.get('chunk_text', '')}"
        for i, c in enumerate(chunks)
    )
    return f"Retrieved context ({len(chunks)} chunks) â€” cite these by their 1-based index:\n\n{listing}"


@answer_agent.output_validator
def _ground_citations(ctx: RunContext[AnswerDeps], out: GroundedAnswer) -> GroundedAnswer:
    n = len(ctx.deps.chunks)
    for c in out.citations:
        if c.source_id > n:
            raise ModelRetry(
                f"citation source_id={c.source_id} does not exist â€” only {n} chunks were retrieved "
                f"(valid ids: 1..{n}). Cite only provided sources; never invent a page."
            )
    if not out.insufficient_context and n > 0 and not out.citations:
        raise ModelRetry(
            "you answered from context but cited nothing â€” cite at least one [Source N], or set "
            "insufficient_context=true if the context truly didn't cover it."
        )
    return out


def _build_model(model: str):
    if not model.startswith("google:"):
        return model
    from google import genai
    from google.genai.types import HttpOptions, HttpRetryOptions
    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider
    model_name = model.split(":", 1)[1]
    client = genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options=HttpOptions(
            timeout=15000,
            retry_options=HttpRetryOptions(attempts=1),
        ),
    )
    return GoogleModel(model_name, provider=GoogleProvider(client=client))


async def run_answer_agent(
    question: str,
    chunks: list[dict],
    *,
    model: str = MODEL,
) -> GroundedAnswer:
    """Run the grounded answer agent over the retrieved chunks."""
    deps = AnswerDeps(question=question, chunks=chunks)
    res = await answer_agent.run(question, deps=deps, model=_build_model(model))
    return res.output
