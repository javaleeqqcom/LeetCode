# Runner backend scaling

- Workers: `[1, 4, 8, 16]`; repeats: 5; logical CPUs: 24; configured maximum: 16.
- Each cell is `median wall seconds (speedup against the same backend at 1 worker)`.
- Persistent rows are warm-pool timings; their one-time pool/source startup is reported separately.
- Native and legacy rows include their per-run process startup; every row includes communication and result digest validation.

## tiny_100k

| Backend | 1 | 4 | 8 | 16 | Best | Pool startup at best | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| Persistent CPython | 0.4689 (1.00×) | 0.1369 (3.42×) | 0.0955 (4.91×) | 0.0894 (5.25×) | 16 workers / 0.0894s | 0.6848s | 463 MiB |
