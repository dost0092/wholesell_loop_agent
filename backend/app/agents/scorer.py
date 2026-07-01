"""Phase 3 — deal scoring engine.

Two implementations:
- HeuristicScorer: deterministic, no API key needed. Always available.
- ClaudeScorer: uses Anthropic when ANTHROPIC_API_KEY is set, with graceful
  fallback to the heuristic scorer on any error.

The factory picks Claude when a key is present, otherwise the heuristic.
"""

from __future__ import annotations

import json
import logging

from app.adapters.interfaces import DealScorer, ScoreResult
from app.config import get_settings

logger = logging.getLogger(__name__)

# Weight each distress signal by urgency / motivation.
_SIGNAL_WEIGHTS = {
    "tax_sale_scheduled": 32,
    "tax_deed_scheduled": 32,
    "tax_delinquent": 18,
    "pre_foreclosure": 28,
    "vacant": 15,
    "probate": 20,
    "code_violation": 12,
}


def _money(raw: dict, *keys: str) -> float | None:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return None


class HeuristicScorer(DealScorer):
    name = "heuristic"

    def score(self, lead: dict) -> ScoreResult:
        signals = lead.get("distress_signals") or []
        raw = lead.get("raw_data") or {}

        score = 20  # baseline for any distressed lead
        reasons: list[str] = []

        for signal in signals:
            weight = _SIGNAL_WEIGHTS.get(signal, 8)
            score += weight
            reasons.append(f"{signal.replace('_', ' ')} (+{weight})")

        # Financial pressure: a larger delinquent balance signals more motivation.
        delinquent = _money(raw, "delinquent_amount", "minimum_bid", "opening_bid")
        adjudged = _money(raw, "adjudged_value")
        estimated_arv = adjudged
        estimated_equity = None

        if delinquent:
            if delinquent >= 50_000:
                score += 12
                reasons.append("high delinquent balance >$50k (+12)")
            elif delinquent >= 10_000:
                score += 8
                reasons.append("moderate delinquent balance >$10k (+8)")
            else:
                score += 4
                reasons.append("low delinquent balance (+4)")

        if adjudged and delinquent and adjudged > delinquent:
            estimated_equity = round(adjudged - delinquent, 2)
            equity_ratio = estimated_equity / adjudged
            if equity_ratio >= 0.7:
                score += 10
                reasons.append("strong equity spread (+10)")
            elif equity_ratio >= 0.4:
                score += 6
                reasons.append("moderate equity spread (+6)")

        # Owner-occupancy heuristic: LLC owners are often investors, less motivated
        owner = str(raw.get("owner_of_record") or "").upper()
        if owner and any(tok in owner for tok in (" LLC", " INC", " CORP", " TRUST", " LP")):
            score -= 6
            reasons.append("entity-owned, likely investor (-6)")

        score = max(0, min(100, score))

        motivation = self._motivation(score, signals)
        offer = self._offer_strategy(score, delinquent, estimated_equity)

        return ScoreResult(
            deal_score=score,
            score_reasoning="; ".join(reasons) or "No distress signals recorded",
            motivation_summary=motivation,
            offer_strategy=offer,
            estimated_arv=estimated_arv,
            estimated_equity=estimated_equity,
            provider=self.name,
        )

    @staticmethod
    def _motivation(score: int, signals: list[str]) -> str:
        if score >= 75:
            level = "Very high"
        elif score >= 55:
            level = "High"
        elif score >= 35:
            level = "Moderate"
        else:
            level = "Low"
        sig = ", ".join(s.replace("_", " ") for s in signals) or "no explicit signals"
        return f"{level} motivation. Distress indicators: {sig}."

    @staticmethod
    def _offer_strategy(score: int, delinquent: float | None, equity: float | None) -> str:
        if score >= 70:
            base = "Prioritize outreach. Lead with a fast, as-is cash close to relieve tax pressure."
        elif score >= 45:
            base = "Warm lead. Emphasize solving the tax burden and a flexible closing timeline."
        else:
            base = "Nurture lead. Low-pressure introduction; monitor for status changes."
        if delinquent:
            base += f" Known delinquency ~${delinquent:,.0f}."
        if equity:
            base += f" Estimated equity ~${equity:,.0f} leaves room for a win-win offer."
        return base


class ClaudeScorer(DealScorer):
    name = "claude"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model
        self._fallback = HeuristicScorer()

    def score(self, lead: dict) -> ScoreResult:
        try:
            import anthropic
        except ImportError:
            logger.warning("anthropic package not installed; using heuristic scorer")
            return self._fallback.score(lead)

        prompt = self._build_prompt(lead)
        try:
            client = anthropic.Anthropic(api_key=self._api_key)
            response = client.messages.create(
                model=self._model,
                max_tokens=600,
                system=(
                    "You are a real estate acquisitions analyst scoring distressed-property "
                    "leads for a wholesaling operation. Respond ONLY with strict JSON."
                ),
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(block.text for block in response.content if hasattr(block, "text"))
            data = json.loads(_extract_json(text))
            return ScoreResult(
                deal_score=int(max(0, min(100, data["deal_score"]))),
                score_reasoning=str(data.get("score_reasoning", "")),
                motivation_summary=str(data.get("motivation_summary", "")),
                offer_strategy=str(data.get("offer_strategy", "")),
                estimated_arv=data.get("estimated_arv"),
                estimated_equity=data.get("estimated_equity"),
                provider=self.name,
            )
        except Exception as exc:  # noqa: BLE001 — never break the pipeline on LLM error
            logger.warning("Claude scoring failed (%s); falling back to heuristic", exc)
            return self._fallback.score(lead)

    @staticmethod
    def _build_prompt(lead: dict) -> str:
        return (
            "Score this distressed property lead from 0-100 for deal potential and seller "
            "motivation. Return JSON with keys: deal_score (int 0-100), score_reasoning, "
            "motivation_summary, offer_strategy, estimated_arv (number or null), "
            "estimated_equity (number or null).\n\n"
            f"Lead data:\n{json.dumps(lead, default=str, indent=2)}"
        )


def _extract_json(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def get_scorer() -> DealScorer:
    settings = get_settings()
    if settings.anthropic_api_key:
        return ClaudeScorer(settings.anthropic_api_key, settings.anthropic_model)
    return HeuristicScorer()
