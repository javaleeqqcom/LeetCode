
from tools.cases_generator import *
if __name__ == "__main__":
    import pandas as pd
    import numpy as np

    budgets = sample_lognormal_scales(
        100,
        mean_scale=100,
    )

    nm = quantize_size_2D(
        budgets,
        beta=(5, 5),
    )

    n = nm[:, 0]
    m = nm[:, 1]

    df = pd.DataFrame({
        "budget": budgets,
        "n": n,
        "m": m,
        "n*m": n * m,
        "ratio": n / np.maximum(m, 1),
        "error": (n * m) / (1+budgets),
    })

    print(df.head(20))

    print()
    print("====== statistics ======")

    print("budget mean :", budgets.mean())
    print("n*m mean    :", (n * m).mean())

    print("ratio mean  :", (n / np.maximum(m, 1)).mean())

    print("error mean  :", ((n * m) / budgets).mean())
    print("error std   :", ((n * m) / budgets).std())
