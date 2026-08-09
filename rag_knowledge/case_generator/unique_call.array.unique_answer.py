# @EXAMPLE_BEGIN: Unique Answer Array Construction
# @EXAMPLE_TAG: unique_call, array, unique_answer, constructive, linear

import random


# @RAG_BEGIN: unique_answer_linear_construction
# @RAG_EXPORT: yes

def case_generator(scale: float) -> dict:
    """Construct one guaranteed pair and collision-free noise in O(n).

    Use this pattern when a problem promises that exactly one pair/solution
    exists. Do not choose dependent parameters independently and do not use
    ``while True`` or enumerate all O(n^2) pairs to validate random samples.
    """
    n = max(2, min(100_000, int(round(scale))))

    # One intentional answer for target == 0.
    answer_value = random.randint(1, 50_000)
    nums = [answer_value, -answer_value]

    # All noise is positive, distinct, and excludes answer_value. Therefore:
    # - two noise values cannot sum to zero;
    # - noise cannot pair with -answer_value to make zero;
    # - the intentional pair is the unique answer.
    noise_start = 100_001
    nums.extend(noise_start + index for index in range(n - 2))
    random.shuffle(nums)

    return {"input": (nums, 0)}

# @RAG_END

# @EXAMPLE_END
