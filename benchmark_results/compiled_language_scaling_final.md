# C/C++ and Python OJ scaling

Workers: `[1, 4, 8, 16]`; repeats: `3`.
Compiled wall time excludes compilation and includes native process startup.

## binary_search_10k_n256

| Backend | 1 | 4 | 8 | 16 | Compile |
|---|---:|---:|---:|---:|---:|
| native_process_manager_standard_cpp | 0.2037s (1.00×) | 0.0907s (2.25×) | 0.0947s (2.15×) | 0.1461s (1.39×) | 2.361s |
| persistent_cpython_standard | 0.1499s (1.00×) | 0.0493s (3.04×) | 0.0451s (3.32×) | 0.0318s (4.72×) | 0.000s |

## integer_mix_100k

| Backend | 1 | 4 | 8 | 16 | Compile |
|---|---:|---:|---:|---:|---:|
| native_process_manager_standard_c | 0.1737s (1.00×) | 0.0831s (2.09×) | 0.0850s (2.04×) | 0.2173s (0.80×) | 0.000s |
| native_process_manager_standard_cpp | 0.1697s (1.00×) | 0.0750s (2.26×) | 0.0797s (2.13×) | 0.1129s (1.50×) | 0.000s |
| persistent_cpython_standard | 0.4676s (1.00×) | 0.1744s (2.68×) | 0.1641s (2.85×) | 0.0835s (5.60×) | 0.000s |

## integer_mix_10k

| Backend | 1 | 4 | 8 | 16 | Compile |
|---|---:|---:|---:|---:|---:|
| native_process_manager_standard_c | 0.0566s (1.00×) | 0.0434s (1.31×) | 0.0578s (0.98×) | 0.0994s (0.57×) | 2.244s |
| native_process_manager_standard_cpp | 0.0421s (1.00×) | 0.0462s (0.91×) | 0.0791s (0.53×) | 0.0971s (0.43×) | 2.348s |
| persistent_cpython_standard | 0.0476s (1.00×) | 0.0193s (2.46×) | 0.0213s (2.24×) | 0.0283s (1.68×) | 0.000s |

## lcs_128_n400

| Backend | 1 | 4 | 8 | 16 | Compile |
|---|---:|---:|---:|---:|---:|
| native_process_manager_standard_cpp | 0.0560s (1.00×) | 0.0454s (1.23×) | 0.0551s (1.02×) | 0.0982s (0.57×) | 2.329s |
| persistent_cpython_standard | 2.0262s (1.00×) | 0.5903s (3.43×) | 0.3905s (5.19×) | 0.3038s (6.67×) | 0.000s |

## matrix_64_n32

| Backend | 1 | 4 | 8 | 16 | Compile |
|---|---:|---:|---:|---:|---:|
| native_process_manager_standard_cpp | 0.0347s (1.00×) | 0.0397s (0.87×) | 0.0608s (0.57×) | 0.0951s (0.36×) | 2.276s |
| persistent_cpython_standard | 0.1675s (1.00×) | 0.0553s (3.03×) | 0.0452s (3.71×) | 0.0387s (4.33×) | 0.000s |

## sieve_count_512_n5k

| Backend | 1 | 4 | 8 | 16 | Compile |
|---|---:|---:|---:|---:|---:|
| native_process_manager_standard_cpp | 0.0331s (1.00×) | 0.0396s (0.84×) | 0.0552s (0.60×) | 0.1579s (0.21×) | 2.325s |
| persistent_cpython_standard | 0.1608s (1.00×) | 0.0570s (2.82×) | 0.0429s (3.74×) | 0.0349s (4.61×) | 0.000s |

## sort_checksum_2k_n512

| Backend | 1 | 4 | 8 | 16 | Compile |
|---|---:|---:|---:|---:|---:|
| native_process_manager_standard_cpp | 0.0982s (1.00×) | 0.0717s (1.37×) | 0.0911s (1.08×) | 0.1026s (0.96×) | 2.426s |
| persistent_cpython_standard | 0.0649s (1.00×) | 0.0260s (2.50×) | 0.0285s (2.27×) | 0.0245s (2.65×) | 0.000s |

## vector_checksum_10k_n64

| Backend | 1 | 4 | 8 | 16 | Compile |
|---|---:|---:|---:|---:|---:|
| native_process_manager_standard_cpp | 0.0855s (1.00×) | 0.0631s (1.35×) | 0.0708s (1.21×) | 0.1238s (0.69×) | 2.346s |
| persistent_cpython_standard | 0.1290s (1.00×) | 0.0417s (3.09×) | 0.0348s (3.70×) | 0.0261s (4.94×) | 0.000s |
