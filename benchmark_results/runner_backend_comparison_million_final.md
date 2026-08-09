# Runner backend scaling

- Workers: `[1, 2, 4, 6, 8, 12, 16]`; repeats: 1; logical CPUs: 24; configured maximum: 16.
- Each cell is `median wall seconds (speedup against the same backend at 1 worker)`.
- Persistent rows are warm-pool timings; their one-time pool/source startup is reported separately.
- Native and legacy rows include their per-run process startup; every row includes communication and result digest validation.

## tiny_1m

| Backend | 1 | 2 | 4 | 6 | 8 | 12 | 16 | Best | Pool startup at best | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C++ manager + CPython | 7.7674 (1.00×) | 4.1128 (1.89×) | 2.4399 (3.18×) | 1.7687 (4.39×) | 1.7209 (4.51×) | 1.2520 (6.20×) | 1.1708 (6.63×) | 16 workers / 1.1708s | n/a | 434 MiB |
| Persistent CPython | 7.6118 (1.00×) | 4.0160 (1.90×) | 2.3368 (3.26×) | 1.7429 (4.37×) | 1.5001 (5.07×) | 1.2704 (5.99×) | 1.2406 (6.14×) | 16 workers / 1.2406s | 0.6943s | 509 MiB |
