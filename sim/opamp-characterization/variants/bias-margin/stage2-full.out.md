# 15-point comparison, ic075 vs canonical (generated)

| Point | Gain dB (c / v) | PM deg (c / v) | Pq uW (c / v) | Fall SR (c / v / d) | Rise SR (c / v) | ICMR-aware fall avg (c / v), class (c / v) | I(XMS) uA |
|---|---|---|---|---|---|---|---|
| FF/-40C/1.98V | 64.93 / 64.93 | 68.40 / 66.96 | 131.5 / 153.2 | 15.27 / 18.66 / 3.39 | 20.82 / 20.78 | 15.35 / 17.83, slew_limited / inconclusive | 0.0000 |
| FF/27C/1.98V | 64.45 / 64.45 | 65.96 / 64.42 | 131.7 / 152.9 | 15.18 / 19.32 / 4.15 | 20.89 / 20.85 | 15.17 / 18.50, slew_limited / inconclusive | 0.0001 |
| FF/125C/1.98V | 63.28 / 63.29 | 64.10 / 62.32 | 131.9 / 153.0 | 14.97 / 19.92 / 4.95 | 20.80 / 20.75 | 14.92 / 19.38, slew_limited / slew_limited | 0.0114 |
| FS/-40C/1.8V | 63.49 / 63.49 | 68.85 / 67.40 | 117.4 / 136.0 | 13.83 / 15.49 / 1.66 | 20.18 / 20.17 | 14.56 / 14.47, slew_limited / slew_limited | 0.0000 |
| FS/27C/1.8V | 62.94 / 62.94 | 66.54 / 65.01 | 117.8 / 136.3 | 14.17 / 16.50 / 2.33 | 20.34 / 20.30 | 14.35 / 14.75, slew_limited / inconclusive | 0.0001 |
| FS/125C/1.8V | 61.64 / 61.64 | 64.64 / 62.90 | 118.3 / 136.7 | 14.10 / 17.36 / 3.25 | 20.35 / 20.30 | 14.01 / 15.42, slew_limited / inconclusive | 0.0056 |
| SF/-40C/1.8V | 68.24 / 68.24 | 65.40 / 63.91 | 118.5 / 136.3 | 14.96 / 16.87 / 1.91 | 20.54 / 20.51 | 15.14 / 15.53, slew_limited / inconclusive | 0.0000 |
| SF/27C/1.8V | 67.77 / 67.77 | 63.94 / 62.42 | 118.8 / 136.4 | 15.02 / 17.29 / 2.27 | 20.72 / 20.67 | 15.04 / 16.04, slew_limited / inconclusive | 0.0001 |
| SF/125C/1.8V | 66.75 / 66.75 | 64.15 / 62.51 | 119.2 / 136.7 | 15.04 / 17.87 / 2.82 | 20.71 / 20.66 | 15.00 / 17.01, slew_limited / inconclusive | 0.0079 |
| SS/-40C/1.62V | 66.98 / 66.98 | 66.25 / 64.81 | 104.1 / 119.0 | 11.03 / 12.00 / 0.97 | 19.88 / 19.87 | 13.95 / 13.65, slew_limited / slew_limited | 0.0000 |
| SS/27C/1.62V | 66.45 / 66.45 | 64.63 / 63.15 | 104.9 / 119.8 | 13.22 / 13.95 / 0.73 | 20.12 / 20.09 | 13.92 / 13.66, slew_limited / slew_limited | 0.0000 |
| SS/125C/1.62V | 65.26 / 65.26 | 64.56 / 62.98 | 105.5 / 120.6 | 13.74 / 14.94 / 1.20 | 20.18 / 20.14 | 13.80 / 13.88, slew_limited / slew_limited | 0.0035 |
| TT/-40C/1.8V | 66.35 / 66.35 | 67.48 / 66.02 | 118.0 / 136.1 | 14.52 / 16.31 / 1.79 | 20.43 / 20.40 | 14.88 / 14.99, slew_limited / inconclusive | 0.0000 |
| TT/27C/1.8V | 65.81 / 65.81 | 65.43 / 63.91 | 118.3 / 136.2 | 14.64 / 16.88 / 2.24 | 20.59 / 20.55 | 14.72 / 15.36, slew_limited / inconclusive | 0.0001 |
| TT/125C/1.8V | 64.63 / 64.63 | 64.28 / 62.61 | 118.7 / 136.6 | 14.59 / 17.53 / 2.94 | 20.60 / 20.55 | 14.53 / 16.16, slew_limited / inconclusive | 0.0060 |

Worst gain: canonical 61.638 @ ('fs', 125.0, 1.8); ic075 61.643 @ ('fs', 125.0, 1.8)

Worst PM: canonical 63.939 @ ('sf', 27.0, 1.8); ic075 62.318 @ ('ff', 125.0, 1.98)

Worst Pq (uW): canonical 131.924 @ ('ff', 125.0, 1.98); ic075 153.157 @ ('ff', -40.0, 1.98)

Worst fall SR: canonical 11.030 @ ('ss', -40.0, 1.62); ic075 11.996 @ ('ss', -40.0, 1.62)

Unit errors: ['20261012-002038-7d10f60-12f3e2: ac-iq: klt sim exit 1: no JSON report on stdout ({\n  "schema_version": 1,\n  "error": {\n    "command": "sim",\n    "message": "batch backend failed: batch-fleet-provision.sh launch failed (exit 1): error: 9 instance(s) already running + 1 requested exceeds BATCH_MAX_CONCURRENT_INSTANCES=8"\n  }\n})', '20261012-002038-7d10f60-12f3e2: ac: klt sim exit 1: no JSON report on stdout ({\n  "schema_version": 1,\n  "error": {\n    "command": "sim",\n    "message": "batch backend failed: batch-fleet-provision.sh launch failed (exit 1): error: 9 instance(s) already running + 1 requested exceeds BATCH_MAX_CONCURRENT_INSTANCES=8"\n  }\n})']
