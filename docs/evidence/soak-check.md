# Soak check (live-rate, synthetic)

- Load: 20 beds x 30 live-rate ticks (6 vitals/bed/tick)
- Observations accepted: 3,600 · Errors: 0
- Wall time: 97.63 s · Throughput: 36.9 obs/s
- Tick latency (seconds): median 3.225, p95 3.435, max 3.716
- Audit chain valid: `True` · /ready: `True`
- **Passed: `True`**

Live-rate shape: one new hour of vitals per bed per tick. Distinct from the 48-hour backfill stress in `docs/scalability.md`. Synthetic data only.
