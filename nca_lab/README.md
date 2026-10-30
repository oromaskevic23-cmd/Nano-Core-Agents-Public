# NCA Synthetic Policy Exercise Lab

**Status: offline exercise.** The program simulates decisions against a small,
explicit mock policy. It does not run, train, dispatch or count real Nano Core
Agents, authenticate a passport, implement Guardian Core, validate a receipt,
perform a payment, access a customer, or grant production authority.

## What the exercise covers

A synthetic case selects one action (`DRAFT`, `DISPATCH`, `PUBLISH`, or
`PAYMENT_CONFIRM`), a classification and seven boolean conditions representing
passport, skill, Guardian, domain, approval, kill switch and external receipt.
It holds missing gates, non-public publication and payment confirmation
without a simulated external receipt. `SIMULATED_ALLOW` is only an exercise
result; `real_execution_allowed` is always false. These input booleans are
assumptions, not evidence or actual verified approvals.

The separate reference predicate expresses the same modeled rules and is
checked against the exercise implementation. Neither is independent human
QA or a proof that the production policy is correct. Random sampling repeats
combinations from a finite matrix; a million draws are not a million distinct
real-world situations. Use separately authored, realistic task data and real
agent responses before making agent-performance claims.

## Reproduce

Requires Python 3.11+ and no external services or credentials.

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 nca_lab/simulator.py --cases 1000000 --seed 20261030
```

The run checks **1,536 distinct mock gate combinations** exhaustively, then
samples the requested number (up to one million) with the given seed. It
reports the decision counts, mismatches and a case-stream SHA-256; repeated
runs are comparable in the same Python environment. No individual records or
customer information are retained. Python version and seed should accompany
any independently reproduced result.

## Recorded local run — 30 October 2026

Python 3.12.14; seed 20261030. One million random draws: 15,015 simulated
allows, 984,985 simulated holds, zero mismatches against the in-process
reference predicate. The additional exhaustive matrix covered 1,536
combinations. Ten unit tests passed locally. Case-stream SHA-256:
`b3a95db63ee3f4665a8eb02ae8a726fdf8f38fdffdd29a155ab3b09efa9b66ed`.
No real agent was trained or executed, and no external effect occurred.

## Next steps

1. Add rights-cleared, synthetic multi-step engineering and commercial
   exercises with expected results written by a separate reviewer.
2. Connect an explicitly authorized, isolated NCA test runner that receives
   scenarios and returns proposals only; capture model/version and outcomes.
3. Score task quality, privacy and safety on a frozen independently authored
   set. Keep model training, scenario execution and production deployment as
   distinct milestones.
4. Preserve federated orchestration and the AI Passport, Enterprise Skills,
   Guardian Core, Approval Gateway, Runtime Domains and Audit Ledger boundaries.
