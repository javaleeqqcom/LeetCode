#ifndef SAFE_ITER_BASE_H
#define SAFE_ITER_BASE_H

#include <Python.h>
#include <stddef.h>
#include "uthash.h"
#include "utarray.h"
#include "container.h"

typedef enum{
    FALSE = 0,
    TRUE = 1
}BOOL;

typedef struct {
    // node 必须放在首位，兼容多种结构体
    PyObject* node;       // 原生节点指针（不增加引用计数）
    Py_ssize_t c_index;      // -1 表示首次出现，>=0 表示重复指向的索引
    // 禁止定义 BigInt vid 因为只有树才会用到，此处定义 CheckEntry 是为了能够统一提取 uf_index，因为结构体排在前面的元素内存一致
} CheckEntry;
// 无需定义树所需的结构体，因为 safe_iter_base 代码中不识别，只需在 Cython 中使用前缀相同的结构体即可，直接透明传输到 check_record PUSH 即可。

/* ---------- 哈希表项（用于 _seen） ---------- */
typedef struct SeenEntry {
    PyObject* key;        // 节点指针作为键
    Py_ssize_t c_index;         // 在 _revisit 中的索引
    UT_hash_handle hh;    // uthash 句柄
} SeenEntry;

/* ---------- SafeIter 核心结构 ---------- */
typedef struct SafeIter {
    SeenEntry* seen;
    UT_array* check_record;
    Py_ssize_t repeat_num;

    // ❌ 删除 cur（或仅作为缓存）
    // CheckEntry cur;

    Py_ssize_t cur_index; // check_record[cur_index] 即为当前迭代输出元素（不可迭代则置为 -1）

    // ------- 将 Cython定义的 _prepare_next 桥接到 SafeIterBase.c 的 prepare 方法中 -----------
    void* ctx; 
    prepare_next_fn prepare; 
} SafeIter;

/* 函数声明 */
void safe_iter_init(SafeIter* it, UT_icd *RevisitEntry_icd);
// 相当于 __del__，释放资源
void safe_iter_free(SafeIter* it);

// 检查 check_record 尾部节点是否重复。返回 TRUE 表示新节点（安全），FALSE 表示重复节点（不安全）。
// 副作用：更新尾部元素的 c_index；若重复，可能更新首次出现节点的 c_index 并增加 repeat_num。
BOOL safe_iter_check_safe(SafeIter* it);

/* 辅助内联函数：获取 check_record 数组元素个数 */
static inline const Py_ssize_t safe_iter_size(const SafeIter* it) {
    return utarray_len(it->check_record);
}
// 返回空 CheckEntry
static inline CheckEntry null_entry(){
    CheckEntry res;
    res.node = NULL;
    res.c_index = -1;
    return res;
};

/* 获取 check_record 第最后一个元素的指针 */
static inline CheckEntry* safe_iter_tail(SafeIter* it) {
    return (CheckEntry*)utarray_back(it->check_record);
}

// ✅ 新增：push 一个 entry（不检查）返回 push 的下标
static inline Py_ssize_t safe_iter_push_raw(SafeIter* it, const void* src) {
    Py_ssize_t index = utarray_len(it->check_record);
    utarray_push_back(it->check_record, (const void*)src);
    // 最好加一个 如果 utarray_push_back 失败 则报 MemERR 错误
    return index;
}

/* 获取 check_record 第 idx 个元素的指针 */
static inline const CheckEntry* safe_iter_get_revisit(const SafeIter* it, Py_ssize_t idx) {
    return (const CheckEntry*)utarray_eltptr(it->check_record, idx);
}

// 子类实现 __next__ 所需要的函数
// C函数 + context指针 的函数指针
typedef void (*prepare_next_fn)(SafeIter*, void* );
inline CheckEntry safe_iter_next(SafeIter* it);

// 不持有 Python Object 的情况下高速迭代
CheckEntry safe_iter_skip_next(SafeIter* it, Py_ssize_t index);

// 消费迭代器展开 [(revisit索引，节点指针),...]
UT_array* safe_iter_flatten_entrys(SafeIter* it, Py_ssize_t max_len);

CheckEntry* safe_iter_revisit_nodes(const SafeIter* it, Py_ssize_t* out_len);

// --------------- 其他 inline 函数 ---------------------------
/* 判空 */
static inline int _is_null(PyObject* node) {
    return (node == NULL || node == Py_None);
}

static inline Py_ssize_t _limit_size(Py_ssize_t size) {
    // 如果 size < 0（通常表示无限制），直接返回最大上限-1（预留1个空位防止 +=1 操作移除，若手动代入最大正值，允许突破限制）
    if (size < 0) return PY_SSIZE_T_MAX-1;
    return size;
}

#endif SAFE_ITER_BASE_H