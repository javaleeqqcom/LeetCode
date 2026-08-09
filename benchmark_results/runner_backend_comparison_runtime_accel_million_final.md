# Runner backend scaling

- Workers: `[1, 4, 8, 16]`; repeats: 2; logical CPUs: 24; configured maximum: 16.
- Each cell is `median wall seconds (speedup against the same backend at 1 worker)`.
- Persistent rows are warm-pool timings; their one-time pool/source startup is reported separately.
- Native and legacy rows include their per-run process startup; every row includes communication and result digest validation.

## tiny_1m

| Backend | 1 | 4 | 8 | 16 | Best | Pool startup at best | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| Persistent CPython | 4.8498 (1.00×) | 1.4427 (3.36×) | 0.9394 (5.16×) | 0.6700 (7.24×) | 16 workers / 0.6700s | 0.6714s | 552 MiB |
