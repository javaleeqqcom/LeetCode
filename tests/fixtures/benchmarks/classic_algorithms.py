class Solution:
    def integer_mix(self, value: int, rounds: int) -> int:
        state = value & 0xFFFFFFFF
        for _ in range(rounds):
            state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
            state ^= state >> 13
        return state

    def vector_checksum(self, values: list[int]) -> int:
        checksum = 0
        for index, value in enumerate(values, start=1):
            checksum = (checksum + index * value) & 0xFFFFFFFFFFFFFFFF
        return checksum

    def binary_search(self, nums: list[int], target: int) -> int:
        left, right = 0, len(nums) - 1
        while left <= right:
            middle = (left + right) // 2
            value = nums[middle]
            if value == target:
                return middle
            if value < target:
                left = middle + 1
            else:
                right = middle - 1
        return -1

    def sort_checksum(self, nums: list[int]) -> list[int]:
        nums.sort()
        if not nums:
            return [0, 0, 0]
        return [nums[0], nums[-1], sum(nums) & 0xFFFFFFFF]

    def sieve_count(self, limit: int) -> int:
        if limit < 2:
            return 0
        is_prime = bytearray(b"\x01") * (limit + 1)
        is_prime[0:2] = b"\x00\x00"
        factor = 2
        while factor * factor <= limit:
            if is_prime[factor]:
                multiple = factor * factor
                while multiple <= limit:
                    is_prime[multiple] = 0
                    multiple += factor
            factor += 1
        return sum(is_prime)

    def lcs_length(self, left: str, right: str) -> int:
        if len(left) < len(right):
            left, right = right, left
        previous = [0] * (len(right) + 1)
        for left_char in left:
            current = [0]
            diagonal = 0
            for index, right_char in enumerate(right, start=1):
                above = previous[index]
                if left_char == right_char:
                    current.append(diagonal + 1)
                else:
                    current.append(max(current[-1], above))
                diagonal = above
            previous = current
        return previous[-1]

    def matrix_multiply_checksum(self, size: int, seed: int) -> int:
        matrix_a = [
            [((row * 17 + column * 13 + seed) % 31) - 15 for column in range(size)]
            for row in range(size)
        ]
        matrix_b = [
            [((row * 11 + column * 19 + seed * 3) % 29) - 14 for column in range(size)]
            for row in range(size)
        ]
        matrix_b_columns = list(zip(*matrix_b))
        checksum = 0
        for row_index, row in enumerate(matrix_a, start=1):
            for column_index, column in enumerate(matrix_b_columns, start=1):
                value = sum(left * right for left, right in zip(row, column))
                checksum = (
                    checksum + value * row_index * column_index
                ) & 0xFFFFFFFFFFFFFFFF
        return checksum
