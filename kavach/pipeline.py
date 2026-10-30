"""One check end to end. The app, eval and bench all call this, so they share one code path."""
from pydantic import BaseModel

from kavach.analyzer import analyze
from kavach.anomaly import score_transaction
from kavach.config import load_config
from kavach.fusion import fuse
from kavach.llm.backend import LLMBackend
from kavach.metrics import EnergyMeter, StageTimer
from kavach.rules.engine import evaluate
from kavach.schemas import (AnalyzerResult, AnomalyResult, Answer, RiskAssessment, RulesResult,
                            TransactionContext)


class CheckResult(BaseModel):
    anomaly: AnomalyResult
    rules: RulesResult
    analyzer: AnalyzerResult
    risk: RiskAssessment
    timings: dict[str, float]
    energy_joules: float | None = None
    energy_kind: str | None = None
    model_name: str = ""

    @property
    def total_seconds(self) -> float:
        return sum(self.timings.values())


def preliminary(ctx: TransactionContext, answers: dict[str, Answer], notice_text: str = "",
                cfg: dict | None = None) -> RiskAssessment:
    """Rules + anomaly only: rendered instantly while the LLM runs."""
    cfg = cfg or load_config()
    return fuse(score_transaction(ctx, cfg), evaluate(answers, ctx, notice_text, cfg), None, ctx, cfg)


def run_check(ctx: TransactionContext, answers: dict[str, Answer], notice_text: str = "",
              backend: LLMBackend | None = None, cfg: dict | None = None, use_llm: bool = True) -> CheckResult:
    cfg = cfg or load_config()
    timer, meter = StageTimer(), EnergyMeter(cfg=cfg)
    meter.start()
    with timer.stage("anomaly"):
        anomaly = score_transaction(ctx, cfg)
    with timer.stage("rules"):
        rules = evaluate(answers, ctx, notice_text, cfg)
    with timer.stage("llm"):
        analyzer = (analyze(backend, ctx, answers, notice_text, cfg) if use_llm
                    else AnalyzerResult(available=False, error="LLM disabled"))
    with timer.stage("fusion"):
        risk = fuse(anomaly, rules, analyzer, ctx, cfg)
    joules, kind = meter.stop()
    return CheckResult(anomaly=anomaly, rules=rules, analyzer=analyzer, risk=risk, timings=timer.timings,
                       energy_joules=joules, energy_kind=kind,
                       model_name=getattr(backend, "model_name", "") if use_llm else "")
