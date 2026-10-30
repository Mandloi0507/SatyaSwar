# SatyaSwar Engine: Latency & Real-Time Performance Benchmarks

| Parameter | Measurement |
|---|---|
| **Benchmark Run Date** | 2026-10-30 |
| **Windows Evaluated** | 100 |
| **Window Duration** | 3.5s (Hop: 1.75s) |
| **Target Hardware** | NVIDIA GeForce RTX 4050 Laptop GPU / CUDA |
| **Telephony Profile** | G.711 mu-law (8 kHz narrowband simulation) |
| **Real-Time Factor (p95 RTF)** | **0.0298** (RTF << 1.0 confirms real-time streaming) |
| **p95 Server Total** | **104.3 ms** (Target: < 500 ms) |

---

## Stage-by-Stage Latency Breakdown (ms)

| Stage | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|---|
| Decode | 0.0 | 0.0 | 0.0 | 0.0 |
| Telephony | 4.0 | 4.0 | 4.7 | 5.1 |
| Vad | 88.1 | 86.4 | 98.3 | 116.0 |
| Detector | 0.0 | 0.0 | 0.0 | 0.0 |
| Scoring | 1.7 | 1.8 | 2.1 | 2.2 |
| Total | 93.8 | 91.7 | 104.3 | 122.4 |

---

## Real-Time Compliance Verification
1. **Time to First Score:** 3.5 seconds audio accumulation + ~0.3 seconds server latency = **~3.8s total**.
2. **Subsequent Scores:** Emitted every **1.75 seconds** (50% overlapping hop).
3. **Queue Safety:** Total p95 server processing stays well beneath the 1.75s (1750 ms) hop window, avoiding frame backpressure under normal network conditions.
