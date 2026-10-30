from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

Level = Literal["LOW", "MEDIUM", "HIGH"]
ScamType = Literal[
    "digital_arrest", "investment", "kyc_or_account_block", "relative_in_trouble",
    "lottery_or_refund", "other", "none_detected",
]
Likelihood = Literal["low", "medium", "high"]


class TxnType(str, Enum):
    CASH = "CASH"
    RTGS = "RTGS"
    NEFT = "NEFT"
    IMPS = "IMPS"
    FD_BREAK = "FD_BREAK"
    DD = "DD"
    OTHER = "OTHER"


class TransactionContext(BaseModel):
    customer_age: int = Field(ge=0, le=120)
    avg_monthly_debit_inr: float = Field(ge=0)
    max_single_debit_inr_12m: float = Field(ge=0)
    txn_amount_inr: float = Field(gt=0)
    txn_type: TxnType
    beneficiary_is_new: bool = False
    customer_on_call_at_counter: bool = False
    accompanied_by_unknown_person: bool = False
    payee_reference: str = ""  # payee account / UPI ID typed by staff; masked unless suspected fraud
    staff_notes: str = ""


class AnomalyResult(BaseModel):
    score: int
    amount_ratio: float
    reasons: list[str]
    check_recommended: bool


class Choice(str, Enum):
    YES = "yes"
    NO = "no"
    UNSURE = "unsure"
    SKIP = "skip"


class Answer(BaseModel):
    choice: Choice | None = None  # None for open questions (Q1)
    detail: str = ""


class RuleHit(BaseModel):
    rule_id: str
    weight: float
    matched_text: str
    source: str  # question id, "notice", "staff_notes" or "transaction"
    via: Literal["answer", "text", "transaction"]
    full: bool = True  # False for Unsure answers: counts at reduced weight, never fires floors/overrides


class RulesResult(BaseModel):
    score: float
    hits: list[RuleHit]

    def full_ids(self) -> set[str]:
        return {h.rule_id for h in self.hits if h.full}


class RedFlag(BaseModel):
    flag: str
    evidence: str
    question_id: str | None = None


class LLMAssessment(BaseModel):
    coercion_likelihood: Likelihood
    scam_type: ScamType
    red_flags: list[RedFlag] = Field(default_factory=list, max_length=5)
    inconsistencies: list[str] = Field(default_factory=list, max_length=3)
    staff_summary: str = ""


class GenerationStats(BaseModel):
    prompt_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
    prompt_seconds: float | None = None
    gen_seconds: float | None = None


class AnalyzerResult(BaseModel):
    available: bool
    assessment: LLMAssessment | None = None
    llm_score: float | None = None
    kept_flags: list[RedFlag] = Field(default_factory=list)
    dropped_flags: int = 0
    stats: GenerationStats = Field(default_factory=GenerationStats)
    attempts: int = 0
    error: str | None = None


class EvidenceItem(BaseModel):
    source: Literal["Transaction", "Answer", "Rule", "LLM", "Notice"]
    text: str
    weight: float = 0.0


class RiskAssessment(BaseModel):
    level: Level
    score: float
    scam_type: ScamType
    evidence: list[EvidenceItem]
    overrides_applied: list[str]
    floors_applied: list[str]
    component_scores: dict[str, float | None]
    llm_available: bool


class Transcript(BaseModel):
    text: str
    language: str
    avg_logprob: float
    seconds: float
