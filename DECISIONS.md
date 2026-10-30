# Decisions

Choices made where PLAN.md was ambiguous, or where measurement forced a change. Format: decision — why — cost if wrong.

## M1 · Environment and model

- **Keep Qwen3-4B-Instruct-2507 Q4_K_M, despite the model choice rule.** — The rule says to switch to the fallback when the LLM step is over 25 s. Measured on the reference laptop: the 4B takes 14–32 s on genuine/coached cases and 35–92 s on Hindi-heavy scam cases. Qwen2.5-1.5B is faster (10–21 s) but rated demo 1 (a blatant digital arrest) as "low" and invented facts ("accompanied by an unknown person"), which is worse than no LLM. — Cost if wrong: slower checks. Mitigation: the rules + anomaly card renders instantly, the LLM refines it, and the README reports measured latency.
- **First LLM attempt runs unconstrained; the one retry uses the JSON-schema grammar.** — Measured grammar overhead was about 0.08 s per output token (13 s per 160 tokens) on this CPU. With the JSON shape spelled out in the cached system prompt, the 4B returned valid JSON on the first attempt in every probe; the grammar retry guarantees valid JSON when it doesn't. Setting: `llm.unconstrained_first_attempt`. — Cost if wrong: a failed first attempt costs a second generation.
- **The JSON shape and question list live in the system prompt**, which stays identical across checks so llama.cpp reuses its KV cache (measured: a repeat prompt re-evaluates 1 token instead of 1,079). — Cost if wrong: none found.
- **Output schema bounded: max 3 red flags (plan said 5), max 2 inconsistencies, maxLength on strings; `max_tokens` 512.** — The first smoke run hit the 384-token cap: Devanagari quotes tokenize long, so the JSON was cut mid-string and both attempts failed the same way. — Cost if wrong: fewer LLM-quoted flags on the card; the rules engine still lists every rule hit.
- **Measured CPU on the reference laptop:** prompt processing about 39 tok/s, decoding about 7 tok/s (prebuilt llama-cpp-python 0.3.36 CPU wheel: AVX2, no AVX-512), 8 threads, plugged in. Switching Windows to "Best performance" power mode may help; not yet measured.

## M2 · Rules and privacy

- **YAML answer key renamed from `on` to `choice`, with quoted values.** — PyYAML (YAML 1.1) parses the key `on` and the value `yes` as booleans. — Cost if wrong: none.
- **Text rules scan detail when the button choice is the question's risk answer or Unsure (plan said "Yes or Unsure").** — For Q3 (knows the payee) and Q10 (family call) the risk answer is No, and that detail is exactly where the scam shows ("No, they gave me the RBI safe account number"). — Cost if wrong: slightly more text scanned.
- **Clause words (तो, वरना, लेकिन, but, then, otherwise…) reset the negation window.** — "पैसे नहीं भेजे तो गिरफ्तार कर लेंगे" ("if you don't send money, we'll arrest you") must not count as a negated arrest threat. — Cost if wrong: a few extra negation misses.
- **Nukta removed during normalisation, for both text and patterns.** — NFC doesn't compose characters like फ़/ड़ (they're composition exclusions), so typed and transcribed Hindi could differ. Casefolding is applied to text only, never to patterns (casefold would turn `\B` into `\b`). — Cost if wrong: none found.
- **Rule patterns extended beyond the PLAN.md examples** with Devanagari inflections and loanwords seen in the scenarios (वालों, के अधिकारी, रखने, पोते/भतीजे/नाती, rakhne). Added before any eval run. — Cost if wrong: none.
- **`payee_reference` added to `TransactionContext`.** — The complaint summary needs the suspect account / UPI ID. It's masked unless the officer marks the case as suspected fraud. — Cost if wrong: one more field collected.
- **`account_vintage_months` dropped** (unused; minimal-data rule). `max_single_debit_inr_12m` is scored (+10 when amount ≥ 2× the largest single debit).
- **Evidence guard:** if a quote isn't in the cited answer but is in another one, it's kept and its `question_id` corrected (it's still verbatim). Trailing punctuation is stripped before matching.

## M5a · Scenarios

- **Scenarios were drafted by Claude (an LLM) and still need the author's hand review**, as PLAN.md requires. They were committed (8b6f179) before any eval run or tuning.
