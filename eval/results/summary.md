# Evaluation results

Generated 2026-10-30 13:05 · model `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` · 40 synthetic scenarios (author-written, LLM-drafted, not real complaints) · LLM cache hits 0, fresh calls 40.

## Headline (fused system)

| Metric | Target | Dev | Test | All 40 |
|---|---|---|---|---|
| Scams flagged MEDIUM or HIGH (recall) | ≥ 90% | 12/12 (100%) | 11/12 (92%) | 23/24 (96%) |
| Scams flagged HIGH | report | 10/12 (83%) | 6/12 (50%) | 16/24 (67%) |
| Coached scams flagged MEDIUM or HIGH | report | 2/2 (100%) | 2/3 (67%) | 4/5 (80%) |
| Genuine flagged HIGH (false alarms) | ≤ 10% | 0/8 (0%) | 0/8 (0%) | 0/16 (0%) |
| Genuine flagged MEDIUM or HIGH | ≤ 30% | 3/8 (38%) | 1/8 (12%) | 4/16 (25%) |

## Ablation (all 40)

| Configuration | Scam MEDIUM+ | Scam HIGH | Coached MEDIUM+ | Genuine HIGH | Genuine MEDIUM+ |
|---|---|---|---|---|---|
| Fused (full system) | 23/24 (96%) | 16/24 (67%) | 4/5 (80%) | 0/16 (0%) | 4/16 (25%) |
| Without LLM (rules + transaction, floors, overrides) | 24/24 (100%) | 15/24 (62%) | 5/5 (100%) | 1/16 (6%) | 6/16 (38%) |
| Rules only (rule score + hard overrides) | 20/24 (83%) | 18/24 (75%) | 1/5 (20%) | 0/16 (0%) | 3/16 (19%) |
| LLM only | 19/24 (79%) | 18/24 (75%) | 1/5 (20%) | 0/16 (0%) | 4/16 (25%) |
| Transaction anomaly only | 23/24 (96%) | 15/24 (62%) | 5/5 (100%) | 9/16 (56%) | 13/16 (81%) |
| Baseline: always MEDIUM | 24/24 (100%) | 0/24 (0%) | 5/5 (100%) | 0/16 (0%) | 16/16 (100%) |

## LLM output

- Valid JSON on the first attempt: 40/40 (100%)
- LLM result available (after at most one retry): 40/40 (100%)
- Evidence-guard: 60 quotes kept, 1 dropped

## Latency per check (machine time, excluding speech-to-text)

| Stage | p50 | p95 |
|---|---|---|
| anomaly (ms) | 0.04 | 0.11 |
| rules (ms) | 0.67 | 3.55 |
| fusion (ms) | 0.17 | 0.39 |
| LLM (s, as generated) | 30.6 | 58.8 |
| Total (s) | 30.6 | 58.8 |

LLM timings are from the run that generated each cached result; `python tasks.py bench` measures fresh calls with energy.

## Misses

- **Scam flagged LOW** `da_10` (test, Coached: 'buying a plot', unknown man answers for him): score 30.0 (anomaly 90, rules 10 [DECLINES_FAMILY_CALL], LLM low)
- **Genuine flagged MEDIUM** `gen_04` (dev, Hard negative: passport police verification, visa and tickets): score 37.5 (anomaly 35, rules 25 [AUTHORITY_IMPERSONATION], LLM medium)
- **Genuine flagged MEDIUM** `gen_05` (dev, Hard negative: land case, lawyer's fees for High Court): score 46.2 (anomaly 70, rules 25 [AUTHORITY_IMPERSONATION], LLM medium)
- **Genuine flagged MEDIUM** `gen_07` (dev, Hard negative: senior on call with son, paying new contractor): score 59.0 (anomaly 100, rules 40 [INSTRUCTED_PAYMENT, LIVE_CALL, UNKNOWN_PAYEE], LLM medium); fired: live_call_large_new_payee
- **Genuine flagged MEDIUM** `gen_13` (test, Hard negative: on call with daughter, paying her society dues): score 56.5 (anomaly 90, rules 40 [INSTRUCTED_PAYMENT, LIVE_CALL, UNKNOWN_PAYEE], LLM medium); fired: live_call_large_new_payee

## Per scenario

| id | split | label | coached | level | score | anomaly | rules | LLM | overrides / floors |
|---|---|---|---|---|---|---|---|---|---|
| da_01 | dev | digital_arrest |  | HIGH | 94.0 | 100 | 100 | high | authority_plus_coercion, live_call_authority_instructed, live_call_large_new_payee, secrecy_instruction |
| da_02 | dev | digital_arrest |  | HIGH | 94.0 | 100 | 100 | high | authority_plus_coercion, live_call_authority_instructed, live_call_large_new_payee, secrecy_instruction |
| da_03 | dev | digital_arrest | yes | MEDIUM | 37.8 | 100 | 25 | low | live_call_large_new_payee |
| da_04 | dev | digital_arrest |  | HIGH | 82.8 | 55 | 100 | high | authority_plus_coercion, secrecy_instruction |
| da_05 | dev | digital_arrest |  | HIGH | 94.0 | 100 | 100 | high | authority_plus_coercion, live_call_authority_instructed, live_call_large_new_payee, secrecy_instruction |
| da_06 | test | digital_arrest |  | HIGH | 94.0 | 100 | 100 | high | authority_plus_coercion, live_call_authority_instructed, live_call_large_new_payee, secrecy_instruction |
| da_07 | test | digital_arrest |  | HIGH | 89.0 | 80 | 100 | high | authority_plus_coercion, secrecy_instruction |
| da_08 | test | digital_arrest | yes | MEDIUM | 41.2 | 100 | 35 | low | live_call_large_new_payee |
| da_09 | test | digital_arrest |  | HIGH | 94.0 | 100 | 100 | high | authority_plus_coercion, live_call_authority_instructed, live_call_large_new_payee, secrecy_instruction |
| da_10 | test | digital_arrest | yes | LOW | 30.0 | 90 | 10 | low | – |
| gen_01 | dev | genuine |  | LOW | 24.0 | 80 | 0 | low | – |
| gen_02 | dev | genuine |  | LOW | 25.5 | 65 | 15 | low | – |
| gen_03 | dev | genuine |  | LOW | 21.5 | 70 | 0 | low | – |
| gen_04 | dev | genuine |  | MEDIUM | 37.5 | 35 | 25 | medium | – |
| gen_05 | dev | genuine |  | MEDIUM | 46.2 | 70 | 25 | medium | – |
| gen_06 | dev | genuine |  | LOW | 29.5 | 60 | 30 | low | – |
| gen_07 | dev | genuine |  | MEDIUM | 59.0 | 100 | 40 | medium | live_call_large_new_payee |
| gen_08 | dev | genuine |  | LOW | 24.0 | 80 | 0 | low | – |
| gen_09 | test | genuine |  | LOW | 17.8 | 55 | 0 | low | – |
| gen_10 | test | genuine |  | LOW | 9.2 | 0 | 15 | low | – |
| gen_11 | test | genuine |  | LOW | 7.8 | 15 | 0 | low | – |
| gen_12 | test | genuine |  | LOW | 24.0 | 80 | 0 | low | – |
| gen_13 | test | genuine |  | MEDIUM | 56.5 | 90 | 40 | medium | live_call_large_new_payee |
| gen_14 | test | genuine |  | LOW | 18.0 | 0 | 40 | low | – |
| gen_15 | test | genuine |  | LOW | 27.8 | 60 | 25 | low | – |
| gen_16 | test | genuine |  | LOW | 24.0 | 80 | 0 | low | – |
| inv_01 | dev | investment |  | HIGH | 70.5 | 55 | 65 | high | secrecy_instruction |
| inv_02 | dev | investment | yes | MEDIUM | 43.2 | 65 | 20 | medium | – |
| inv_03 | dev | investment |  | HIGH | 73.5 | 60 | 70 | high | – |
| inv_04 | test | investment |  | MEDIUM | 62.5 | 65 | 35 | high | – |
| inv_05 | test | investment |  | HIGH | 81.8 | 100 | 65 | high | live_call_large_new_payee, secrecy_instruction |
| kyc_01 | dev | kyc_or_account_block |  | HIGH | 89.0 | 80 | 100 | high | authority_plus_coercion, live_call_authority_instructed, live_call_large_new_payee, secrecy_instruction |
| kyc_02 | dev | kyc_or_account_block |  | HIGH | 82.2 | 60 | 95 | high | – |
| kyc_03 | test | kyc_or_account_block |  | HIGH | 82.8 | 55 | 100 | high | – |
| kyc_04 | test | kyc_or_account_block |  | MEDIUM | 62.2 | 15 | 70 | high | – |
| lot_01 | dev | lottery_or_refund |  | HIGH | 74.5 | 50 | 80 | high | secrecy_instruction |
| lot_02 | test | lottery_or_refund |  | HIGH | 70.2 | 40 | 75 | high | authority_plus_coercion |
| rel_01 | dev | relative_in_trouble |  | HIGH | 91.5 | 90 | 100 | high | authority_plus_coercion, live_call_authority_instructed, live_call_large_new_payee, secrecy_instruction |
| rel_02 | test | relative_in_trouble |  | MEDIUM | 41.8 | 60 | 65 | low | – |
| rel_03 | test | relative_in_trouble | yes | MEDIUM | 32.8 | 80 | 25 | low | live_call_large_new_payee |
