# Runner backend scaling

- Workers: `[1, 2, 4, 6, 8, 12, 16]`; repeats: 5; logical CPUs: 24; configured maximum: 16.
- Each cell is `median wall seconds (speedup against the same backend at 1 worker)`.
- Persistent rows are warm-pool timings; their one-time pool/source startup is reported separately.
- Native and legacy rows include their per-run process startup; every row includes communication and result digest validation.

## lcs_128

| Backend | 1 | 2 | 4 | 6 | 8 | 12 | 16 | Best | Pool startup at best | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Persistent CPython | 2.0562 (1.00×) | 1.0353 (1.99×) | 0.5831 (3.53×) | 0.4808 (4.28×) | 0.3599 (5.71×) | 0.3075 (6.69×) | 0.2853 (7.21×) | 16 workers / 0.2853s | 0.6753s | 453 MiB |
