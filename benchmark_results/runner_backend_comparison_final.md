# Runner backend scaling

- Workers: `[1, 2, 4, 6, 8, 12, 16]`; repeats: 3; logical CPUs: 24; configured maximum: 16.
- Each cell is `median wall seconds (speedup against the same backend at 1 worker)`.
- Persistent rows are warm-pool timings; their one-time pool/source startup is reported separately.
- Native and legacy rows include their per-run process startup; every row includes communication and result digest validation.

## lcs_128

| Backend | 1 | 2 | 4 | 6 | 8 | 12 | 16 | Best | Pool startup at best | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Legacy Python | 2.0661 (1.00×) | 1.2842 (1.61×) | 0.8397 (2.46×) | 0.7346 (2.81×) | 0.7587 (2.72×) | 0.7776 (2.66×) | 0.8778 (2.35×) | 6 workers / 0.7346s | n/a | n/a |
| C++ manager + CPython | 2.1671 (1.00×) | 1.2149 (1.78×) | 0.7450 (2.91×) | 0.5837 (3.71×) | 0.5389 (4.02×) | 0.4772 (4.54×) | 0.4702 (4.61×) | 16 workers / 0.4702s | n/a | 438 MiB |
| Persistent CPython | 2.0037 (1.00×) | 1.0618 (1.89×) | 0.5752 (3.48×) | 0.4872 (4.11×) | 0.3581 (5.60×) | 0.3149 (6.36×) | 0.2940 (6.81×) | 16 workers / 0.2940s | 0.6784s | 454 MiB |

## tiny_100k

| Backend | 1 | 2 | 4 | 6 | 8 | 12 | 16 | Best | Pool startup at best | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Legacy Python | 5.2469 (1.00×) | 7.9420 (0.66×) | 5.8813 (0.89×) | 5.9560 (0.88×) | 6.2260 (0.84×) | 6.1784 (0.85×) | 6.3387 (0.83×) | 1 workers / 5.2469s | n/a | n/a |
| C++ manager + CPython | 0.9281 (1.00×) | 0.5530 (1.68×) | 0.3787 (2.45×) | 0.3489 (2.66×) | 0.3257 (2.85×) | 0.3085 (3.01×) | 0.3223 (2.88×) | 12 workers / 0.3085s | n/a | 435 MiB |
| Persistent CPython | 0.8084 (1.00×) | 0.4239 (1.91×) | 0.2333 (3.47×) | 0.1857 (4.35×) | 0.1794 (4.51×) | 0.1377 (5.87×) | 0.1297 (6.23×) | 16 workers / 0.1297s | 0.7277s | 459 MiB |

## tiny_10k

| Backend | 1 | 2 | 4 | 6 | 8 | 12 | 16 | Best | Pool startup at best | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Legacy Python | 0.4961 (1.00×) | 0.8862 (0.56×) | 0.8573 (0.58×) | 0.8647 (0.57×) | 0.8780 (0.57×) | 1.0016 (0.50×) | 0.9927 (0.50×) | 1 workers / 0.4961s | n/a | n/a |
| C++ manager + CPython | 0.2122 (1.00×) | 0.1746 (1.22×) | 0.1647 (1.29×) | 0.1631 (1.30×) | 0.1860 (1.14×) | 0.2433 (0.87×) | 0.2586 (0.82×) | 6 workers / 0.1631s | n/a | 434 MiB |
| Persistent CPython | 0.0792 (1.00×) | 0.0416 (1.90×) | 0.0275 (2.88×) | 0.0187 (4.24×) | 0.0212 (3.74×) | 0.0200 (3.96×) | 0.0254 (3.12×) | 6 workers / 0.0187s | 0.3181s | 454 MiB |

## vector_10k

| Backend | 1 | 2 | 4 | 6 | 8 | 12 | 16 | Best | Pool startup at best | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Legacy Python | 0.9137 (1.00×) | 1.2157 (0.75×) | 0.9730 (0.94×) | 1.0197 (0.90×) | 1.0054 (0.91×) | 1.0792 (0.85×) | 1.2952 (0.71×) | 1 workers / 0.9137s | n/a | n/a |
| C++ manager + CPython | 0.2851 (1.00×) | 0.1962 (1.45×) | 0.1854 (1.54×) | 0.1932 (1.48×) | 0.1907 (1.50×) | 0.2233 (1.28×) | 0.2662 (1.07×) | 4 workers / 0.1854s | n/a | 436 MiB |
| Persistent CPython | 0.1474 (1.00×) | 0.0746 (1.98×) | 0.0427 (3.45×) | 0.0382 (3.86×) | 0.0365 (4.04×) | 0.0303 (4.87×) | 0.0328 (4.49×) | 12 workers / 0.0303s | 0.5199s | 458 MiB |
