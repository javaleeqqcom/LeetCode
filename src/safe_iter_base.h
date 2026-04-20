#ifndef SAFE_ITER_BASE_H
#define SAFE_ITER_BASE_H

#include <Python.h>
#include <stddef.h>
#include "uthash.h"
#include "utarray.h"
#include "container.h"

/* ---------- RevisitEntry（基础版，不含 vid） ---------- */
typedef struct {
    size_t uf_index;      // -1 表示首次出现，>=0 表示重复指向的索引
    PyObject* node;       // 原生节点指针（不增加引用计数）
    // 禁止定义 BigInt vid 因为只有树才会用到，此处定义 RevisitEntry 是为了能够统一提取 uf_index，因为结构体排在前面的元素内存一致
} RevisitEntry;


/* ---------- 哈希表项（用于 _seen） ---------- */
typedef struct SeenEntry {
    PyObject* key;        // 节点指针作为键
    size_t index;         // 在 _revisit 中的索引
    UT_hash_handle hh;    // uthash 句柄
} SeenEntry;

/* ---------- SafeIter 核心结构 ---------- */
typedef struct {
    SeenEntry* seen;
    UT_array* revisit;
    size_t repeat_num;

    PyObject* cur;

    // RevisitEntry 去耦合专用（链表、树 用不同的函数）由 pyx 提供
    PyObject* (*get_node_ptr)(void* entry_ele); // void 是 IterNode 及其派生类型
    void (*push_revisit)(struct SafeIter* it, void* entry_ele);
} SafeIter;

/* 函数声明 */
void safe_iter_init(SafeIter* it, UT_icd *RevisitEntry_icd);
void safe_iter_cleanup(SafeIter* it);
size_t safe_iter_check_safe(SafeIter* it, PyObject* node);

/* 辅助内联函数：获取 revisit 数组元素个数 */
static inline size_t safe_iter_size(const SafeIter* it) {
    return utarray_len(it->revisit);
}

/* 获取第 idx 个元素的指针（只读） */
static inline const RevisitEntry* safe_iter_get_entry(const SafeIter* it, size_t idx) {
    return (const RevisitEntry*)utarray_eltptr(it->revisit, idx);
}

// 需要增加 revisit_nodes

// --------------- 其他 inline 函数 ---------------------------
/* 判空 */
static inline int is_null(PyObject* node) {
    return (node == NULL || node == Py_None);
}

const size_t UPP_SIZE=(size_t)(-2); // 区分 size_t 最大值时可取得的上限（若不减2有从 <size_t>-1 溢出变为 0 的死循环风险）
static inline const size_t _limit_size(Py_ssize_t size){
    return min(UPP_SIZE, (size_t)size);
}

#endif /* SAFE_ITER_BASE_H */