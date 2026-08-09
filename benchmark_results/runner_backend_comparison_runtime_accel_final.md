# Runner backend scaling

- Workers: `[1, 4, 8, 16]`; repeats: 3; logical CPUs: 24; configured maximum: 16.
- Each cell is `median wall seconds (speedup against the same backend at 1 worker)`.
- Persistent rows are warm-pool timings; their one-time pool/source startup is reported separately.
- Native and legacy rows include their per-run process startup; every row includes communication and result digest validation.

## lcs_128

| Backend | 1 | 4 | 8 | 16 | Best | Pool startup at best | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| Persistent CPython | 2.0351 (1.00×) | 0.6453 (3.15×) | 0.3678 (5.53×) | 0.3131 (6.50×) | 16 workers / 0.3131s | 0.6874s | 452 MiB |

## tiny_100k

| Backend | 1 | 4 | 8 | 16 | Best | Pool startup at best | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| Persistent CPython | 0.4800 (1.00×) | 0.1558 (3.08×) | 0.1042 (4.61×) | 0.1027 (4.67×) | 16 workers / 0.1027s | 0.6848s | 463 MiB |

## tiny_10k

| Backend | 1 | 4 | 8 | 16 | Best | Pool startup at best | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| Persistent CPython | 0.0474 (1.00×) | 0.0174 (2.73×) | 0.0161 (2.95×) | 0.0182 (2.61×) | 8 workers / 0.0161s | 0.4160s | 453 MiB |

## vector_10k

| Backend | 1 | 4 | 8 | 16 | Best | Pool startup at best | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| Persistent CPython | 0.1122 (1.00×) | 0.0394 (2.84×) | 0.0289 (3.88×) | 0.0319 (3.51×) | 8 workers / 0.0289s | 0.4243s | 457 MiB |
