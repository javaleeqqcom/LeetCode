class Solution {
public:
    uint32_t integer_mix(long long value, int rounds) {
        uint32_t state = static_cast<uint32_t>(value);
        for (int round = 0; round < rounds; ++round) {
            state = state * UINT32_C(1664525) + UINT32_C(1013904223);
            state ^= state >> 13;
        }
        return state;
    }

    uint64_t vector_checksum(vector<int>& values) {
        uint64_t checksum = 0;
        for (size_t index = 0; index < values.size(); ++index) {
            checksum += static_cast<uint64_t>(index + 1) *
                        static_cast<int64_t>(values[index]);
        }
        return checksum;
    }

    int binary_search(vector<int>& nums, int target) {
        int left = 0;
        int right = static_cast<int>(nums.size()) - 1;
        while (left <= right) {
            const int middle = left + (right - left) / 2;
            if (nums[middle] == target) return middle;
            if (nums[middle] < target) {
                left = middle + 1;
            } else {
                right = middle - 1;
            }
        }
        return -1;
    }

    vector<long long> sort_checksum(vector<int> nums) {
        sort(nums.begin(), nums.end());
        if (nums.empty()) return {0, 0, 0};
        uint32_t checksum = 0;
        for (int value : nums) checksum += static_cast<uint32_t>(value);
        return {nums.front(), nums.back(), checksum};
    }

    int sieve_count(int limit) {
        if (limit < 2) return 0;
        vector<bool> is_prime(static_cast<size_t>(limit) + 1, true);
        is_prime[0] = is_prime[1] = false;
        for (int factor = 2; factor <= limit / factor; ++factor) {
            if (!is_prime[factor]) continue;
            for (int multiple = factor * factor; multiple <= limit; multiple += factor) {
                is_prime[multiple] = false;
            }
        }
        return static_cast<int>(count(is_prime.begin(), is_prime.end(), true));
    }

    int lcs_length(string left, string right) {
        if (left.size() < right.size()) swap(left, right);
        vector<int> previous(right.size() + 1, 0);
        vector<int> current(right.size() + 1, 0);
        for (char left_char : left) {
            fill(current.begin(), current.end(), 0);
            for (size_t index = 1; index <= right.size(); ++index) {
                if (left_char == right[index - 1]) {
                    current[index] = previous[index - 1] + 1;
                } else {
                    current[index] = max(current[index - 1], previous[index]);
                }
            }
            previous.swap(current);
        }
        return previous.back();
    }

    uint64_t matrix_multiply_checksum(int size, int seed) {
        vector<vector<int>> matrix_a(size, vector<int>(size));
        vector<vector<int>> matrix_b(size, vector<int>(size));
        for (int row = 0; row < size; ++row) {
            for (int column = 0; column < size; ++column) {
                matrix_a[row][column] = ((row * 17 + column * 13 + seed) % 31) - 15;
                matrix_b[row][column] = ((row * 11 + column * 19 + seed * 3) % 29) - 14;
            }
        }
        uint64_t checksum = 0;
        for (int row = 0; row < size; ++row) {
            for (int column = 0; column < size; ++column) {
                int64_t value = 0;
                for (int inner = 0; inner < size; ++inner) {
                    value += static_cast<int64_t>(matrix_a[row][inner]) *
                             matrix_b[inner][column];
                }
                checksum += static_cast<uint64_t>(value * (row + 1) * (column + 1));
            }
        }
        return checksum;
    }
};
