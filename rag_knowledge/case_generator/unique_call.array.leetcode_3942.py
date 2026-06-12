# @EXAMPLE_BEGIN: 3942.Minimum Operations to Sort a Permutation
# @EXAMPLE_TAG: permutation, operations, reverse, rotate, leetcode

from typing import Dict, Any
import numpy as np

# @RAG_BEGIN: case_generator_function
# @RAG_EXPORT: no

def case_generator(scale: int) -> Dict[str, Any]:
    """
    Generate a permutation of [0, n-1] by applying a random sequence of
    inverse operations starting from a sorted array.
    Allowed inverse operations:
        - right shift by k (inverse of "rotate left by one")
        - reverse (self‑inverse)
        - random swap of two elements (with small probability, creates
          unreachable states).

    Parameters
    ----------
    scale : int
        Maps directly to permutation length n, clamped to [1, 100000].
        Also used as random seed for reproducibility.

    Returns
    -------
    dict with key "input" mapping to a tuple containing a single list of ints.
    """
# @RAG_END

    # @RAG_BEGIN: scale2n
    # @RAG_EXPORT: depend

    MIN_N: int = 1
    MAX_N: int = 10**5

    n = max(MIN_N, min(MAX_N, scale))
    
    # n = 1 is trivial, always sorted after 0 operations
    if n == 1:
        return {"input": ([0],)}

    rng = np.random.default_rng(scale)

    # @RAG_END

    # @RAG_BEGIN: init_sorted_perm
    # @RAG_EXPORT: no

    # Start from the sorted identity permutation
    arr = np.arange(n, dtype=np.int32)

    # @RAG_END

    # @RAG_BEGIN: ops_count_and_weights
    # @RAG_EXPORT: depend

    # Number of inverse operations to apply: 0 .. n
    ops = rng.integers(0, n + 1)

    # Weights for choosing among three operations:
    #   0 : right shift,  1 : reverse,  2 : random swap (unreachable)
    w_swap = 1.0 / (2 + n)
    weights = np.array([1.0, 1.0, w_swap])

    # @RAG_END

    # @RAG_BEGIN: simulate_operations
    # @RAG_DEP: ops_count_and_weights
    # @RAG_EXPORT: yes

    last_op = -1   # no previous operation initially

    for _ in range(ops):
        # Disallow consecutive shift/reverse to avoid trivial cancellations.
        # Swap is always allowed.
        mask = np.array([last_op != 0, last_op != 1, True])
        valid = weights * mask
        op = rng.choice(3, p=valid / valid.sum())

        if op == 0:
            # Right shift by k (1 <= k <= n-1)
            k = rng.integers(1, n)
            arr = np.roll(arr, k)
        elif op == 1:
            # Reverse the whole array
            arr = np.flip(arr)
        else:
            # Swap two distinct positions
            i, j = rng.choice(n, size=2, replace=False)
            arr[i], arr[j] = arr[j], arr[i]

        last_op = op

    # @RAG_END

    # @RAG_BEGIN: return_input
    # @RAG_EXPORT: no

    return {"input": (arr.tolist(),)}

    # @RAG_END

# @EXAMPLE_END