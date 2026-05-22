#ifndef BIGINT_VID_H
#define BIGINT_VID_H

#include <stddef.h>
#include "utarray.h"

/* ---------- BigInt 结构 ---------- */
typedef struct BigInt {
    size_t small;          // 低位块
    size_t pre;            // 前驱索引（-1 表示无前驱）
    unsigned short bitLen; // 当前总比特长度
} BigInt;

/* ---------- 内联工具函数 ---------- */

static inline size_t fast_bit_len(size_t n) {
    if (n == 0) return 0;
    // 64 位系统使用 __builtin_clzll，32 位系统使用 __builtin_clzl 或 __builtin_clz
    return (sizeof(size_t) * 8) - __builtin_clzll((unsigned long long)n);
}

static inline BigInt bigint_new(size_t num) {
    BigInt r;
    r.small = num;
    r.bitLen = fast_bit_len(num);
    r.pre = (size_t)-1;
    return r;
}

/* ---------- 核心：左移（操作 UT_array 中的某个元素） ---------- */
static inline void bigint_lshift(UT_array* arr, size_t index) {
    const int BITS = sizeof(size_t) * 8;
    BigInt* cur = (BigInt*)utarray_eltptr(arr, index);
    if (cur->bitLen % BITS == 0) {
        cur->small = 0;
        cur->pre = index;          // 按照原 Cython 逻辑：pre 指向自身
    } else {
        cur->small <<= 1;
    }
    cur->bitLen++;
}

static inline BigInt bigint_or1(BigInt cur) {
    cur.small |= 1;
    return cur;
}

#endif /* BIGINT_VID_H */