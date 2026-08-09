# Runner backend scaling

- Workers: `[1, 2, 4, 6, 8, 12, 16]`; repeats: 5; logical CPUs: 24; configured maximum: 16.
- Each cell is `median wall seconds (speedup against the same backend at 1 worker)`.
- Persistent rows are warm-pool timings; their one-time pool/source startup is reported separately.
- Native and legacy rows include their per-run process startup; every row includes communication and result digest validation.

## lcs_128

| Backend | 1 | 2 | 4 | 6 | 8 | 12 | 16 | Best | Pool startup at best | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Persistent CPython | 2.0382 (1.00×) | 1.0553 (1.93×) | 0.5997 (3.40×) | 0.4597 (4.43×) | 0.3685 (5.53×) | 0.3199 (6.37×) | 0.2598 (7.84×) | 16 workers / 0.2598s | 0.6629s | 452 MiB |
