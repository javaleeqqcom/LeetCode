# Runner backend scaling

- Workers: `[1, 4, 8, 16]`; repeats: 5; logical CPUs: 24; configured maximum: 16.
- Each cell is `median wall seconds (speedup against the same backend at 1 worker)`.
- Persistent rows are warm-pool timings; their one-time pool/source startup is reported separately.
- Native and legacy rows include their per-run process startup; every row includes communication and result digest validation.

## tiny_100k

| Backend | 1 | 4 | 8 | 16 | Best | Pool startup at best | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| Persistent CPython | 0.4663 (1.00×) | 0.1497 (3.12×) | 0.0957 (4.87×) | 0.0804 (5.80×) | 16 workers / 0.0804s | 0.6778s | 466 MiB |
