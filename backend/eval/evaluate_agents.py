"""Evaluates the three agents with MLflow (mlflow.genai.evaluate) against a hand-labelled demo inbox.

For every email the real agent chain runs, exactly as in the app:
    Analyst (read_email) → Legal (check) → Negotiator (draft) → Legal (review_draft)
and code-based scorers compare the result with the expected answer:

    analyst_kind        right category (price change / late payment / other)
    analyst_party       right company
    analyst_figures     right figures (% increase, days late) – or correctly "no figures"
    legal_verdict       right verdict (violates / allowed / unclear)
    legal_clause        right contract clause cited
    negotiator_draft    final draft passes the Legal Agent's hard rules (clause, amounts, invoice no.)
    legal_review        Legal Agent approved the final draft
    model_answered      share of steps answered by Granite (1.0) instead of the canned fallback (0.0)

Every row is also an MLflow trace, so a wrong answer can be opened and inspected step by step.

Run (from the backend/ folder, with the model reachable):
    pip install -r eval/requirements.txt
    MLFLOW_TRACKING_URI=http://localhost:5000 LLM_BASE_URL=http://localhost:8000/v1 python eval/evaluate_agents.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `app` importable

os.environ.setdefault("MLFLOW_TRACKING_URI", "http://localhost:5000")
os.environ.setdefault("MLFLOW_GENAI_EVAL_MAX_WORKERS", "2")  # an 8B model on one GPU – don't flood it

import mlflow  # noqa: E402
from mlflow.entities import Feedback  # noqa: E402
from mlflow.genai.scorers import scorer  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402

from app import data  # noqa: E402
from app.agents import analyst, legal, negotiator  # noqa: E402
from app.config import settings  # noqa: E402
from app.llm import llm  # noqa: E402
from app.orchestrator import RECOMMEND, _task  # noqa: E402

EXPERIMENT = os.getenv("MLFLOW_EVAL_EXPERIMENT", "avida-cfo-agent-eval")

# Ground truth for the demo inbox (backend/data/inbox_mock.json), labelled by hand from the emails and contracts.
GOLD = {
    "mail-001": {"kind": "price_change", "party": "CloudHost GmbH", "increase_pct": 15.0,
                 "verdict": "violates", "clause_id": "§5.2", "recommendation": "reject"},
    "mail-002": {"kind": "price_change", "party": "PaperPro GmbH", "increase_pct": 3.5,
                 "verdict": "allowed", "recommendation": "accept"},
    "mail-003": {"kind": "other"},
    "mail-004": {"kind": "payment_delay", "party": "Bauer Maschinenbau AG", "days_late": 30,
                 "verdict": "violates", "clause_id": "§7.1", "recommendation": "remind"},
    "mail-005": {"kind": "price_change", "party": "Stahlhandel Nord GmbH", "increase_pct": 6.0,
                 "verdict": "allowed", "recommendation": "accept"},
    "mail-006": {"kind": "price_change", "party": "IT-Service Kraus e.K.", "figures_stated": False,
                 "verdict": "unclear", "recommendation": "review"},
}


# --- the agent chain under test --------------------------------------------------

async def _chain(email: dict) -> dict:
    steps: dict[str, str] = {}
    ex, steps["analyst.read_email"] = await analyst.read_email(email)
    out = {"kind": ex["kind"], "party": ex.get("party") or ex.get("counterparty", ""),
           "figures_stated": ex.get("figures_stated"), "increase_pct": ex.get("increase_pct"),
           "days_late": ex.get("days_late"), "steps": steps}
    if ex["kind"] == "other":
        return out

    res, steps["legal.check"] = await legal.check(ex, email["received"])
    out.update(verdict=res["verdict"], clause_id=res.get("clause_id"),
               party=ex.get("party", out["party"]))
    finding = {"kind": ex["kind"], "recommendation": RECOMMEND.get((ex["kind"], res["verdict"]), "review")}
    out["recommendation"] = finding["recommendation"]
    task = _task(finding)
    if not task:
        return out

    imp = (analyst.impact(ex) if ex["kind"] == "price_change" and ex["figures_stated"]
           else analyst.delay_impact(ex, [], [analyst.to_delay(ex)]) if ex["kind"] == "payment_delay" and ex["figures_stated"]
           else {"monthly": 0.0, "in_horizon": 0.0, "next_12_months": 0.0, "calculation": ""})
    body, steps["negotiator.draft"] = await negotiator.draft(task, ex, res, imp)
    review, steps["legal.review_draft"] = await legal.review_draft(body, task, ex, res)
    if not review["approved"]:  # same single revision round as the app
        body, steps["negotiator.revise"] = await negotiator.revise(task, body, review["issues"], ex, res, imp)
        review, steps["legal.review_draft#2"] = await legal.review_draft(body, task, ex, res)
    out.update(task=task, draft=body, review_approved=review["approved"],
               rule_issues=legal.rule_review(body, task, ex, res))
    return out


@mlflow.trace(name="agent_chain", span_type="AGENT")
def predict(email_id: str) -> dict:
    """One evaluation row. A fresh HTTP client per row, because every row runs in its own event loop."""
    llm.client = AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key,
                             timeout=settings.llm_timeout_s, max_retries=0)
    email = next(m for m in data.inbox() if m["id"] == email_id)
    return asyncio.run(_chain(email))


# --- scorers ----------------------------------------------------------------------

def _na(why: str) -> Feedback:
    return Feedback(value=None, rationale=f"not applicable: {why}")


@scorer
def analyst_kind(outputs, expectations) -> Feedback:
    ok = outputs["kind"] == expectations["kind"]
    return Feedback(value=ok, rationale=f"got {outputs['kind']}, expected {expectations['kind']}")


@scorer
def analyst_party(outputs, expectations):
    if "party" not in expectations:
        return _na("email is not about a counterparty")
    got, exp = (outputs.get("party") or "").lower(), expectations["party"].lower()
    return Feedback(value=bool(got) and (exp in got or got in exp), rationale=f"got '{outputs.get('party')}'")


@scorer
def analyst_figures(outputs, expectations):
    if expectations["kind"] == "other":
        return _na("no figures expected")
    if expectations.get("figures_stated") is False:
        return Feedback(value=outputs.get("figures_stated") is False,
                        rationale="email has no figures – the agent must not invent any")
    if "increase_pct" in expectations:
        got = outputs.get("increase_pct")
        ok = got is not None and abs(float(got) - expectations["increase_pct"]) < 0.1
        return Feedback(value=ok, rationale=f"increase {got}% vs {expectations['increase_pct']}%")
    got = outputs.get("days_late")
    return Feedback(value=got == expectations["days_late"], rationale=f"{got} days late vs {expectations['days_late']}")


@scorer
def legal_verdict(outputs, expectations):
    if "verdict" not in expectations:
        return _na("nothing to check against a contract")
    return Feedback(value=outputs.get("verdict") == expectations["verdict"],
                    rationale=f"got {outputs.get('verdict')}, expected {expectations['verdict']}")


@scorer
def legal_clause(outputs, expectations):
    if "clause_id" not in expectations:
        return _na("no clause expected")
    return Feedback(value=outputs.get("clause_id") == expectations["clause_id"],
                    rationale=f"cited {outputs.get('clause_id')}, expected {expectations['clause_id']}")


@scorer
def negotiator_draft(outputs):
    if "draft" not in outputs:
        return _na("no email to write")
    issues = outputs.get("rule_issues") or []
    return Feedback(value=not issues, rationale="; ".join(issues) or "clause, amounts and references are in the draft")


@scorer
def legal_review(outputs):
    if "draft" not in outputs:
        return _na("no email to review")
    return Feedback(value=bool(outputs.get("review_approved")), rationale="approved by the Legal Agent"
                    if outputs.get("review_approved") else "Legal Agent still had issues")


@scorer
def model_answered(outputs) -> Feedback:
    steps = outputs.get("steps") or {}
    llm_steps = [k for k, v in steps.items() if v == "llm"]
    share = round(len(llm_steps) / len(steps), 2) if steps else 0.0
    return Feedback(value=share, rationale=f"model answered {len(llm_steps)}/{len(steps)} steps: {steps}")


SCORERS = [analyst_kind, analyst_party, analyst_figures, legal_verdict, legal_clause,
           negotiator_draft, legal_review, model_answered]


def main() -> None:
    from app import tracing

    tracing.init(blocking=True)  # agent spans nest under each evaluation row's trace
    mlflow.set_experiment(EXPERIMENT)
    dataset = [{"inputs": {"email_id": eid}, "expectations": exp} for eid, exp in GOLD.items()]
    run_name = os.getenv("EVAL_RUN_NAME", f"{settings.llm_model}{'' if settings.llm_enabled else '-fallback'}")
    with mlflow.start_run(run_name=run_name):
        mlflow.log_params({"model": settings.llm_model, "llm_base_url": settings.llm_base_url,
                           "llm_enabled": settings.llm_enabled, "emails": len(dataset)})
        result = mlflow.genai.evaluate(data=dataset, predict_fn=predict, scorers=SCORERS)
    print("\nMLflow run:", result.run_id)
    for k, v in sorted(result.metrics.items()):
        print(f"  {k:40s} {v}")


if __name__ == "__main__":
    main()
