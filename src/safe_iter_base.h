#ifndef SAFE_ITER_BASE_H
#define SAFE_ITER_BASE_H

#include <Python.h>
#include <stddef.h>
#include "uthash.h"
#include "utarray.h"
#include "container.h"

/* ---------- RevisitEntry（基础版，不含 vid） ---------- */
#ifndef RevisitEntry
typedef struct {
    size_t uf_index;      // -1 表示首次出现，>=0 表示重复指向的索引
    PyObject* node;       // 原生节点指针（不增加引用计数）
    // BigInt vid; // 仅树需要用到，因此这里仅注释，当使用树时，应手动定义 RevisitEntry 覆盖，并且必须包含前两个变量
} RevisitEntry;

typedef struct {
    PyObject* node;
    // 树节点才会用到的部分
    // int checked;
    // BigInt vid;   
} IterNode;
typedef struct {
    size_t uf_index;      // -1 表示首次出现，>=0 表示重复指向的索引
    PyObject* node;       // 原生节点指针（不增加引用计数）
    // BigInt vid; // 仅树需要用到，因此这里仅注释，当使用树时，应手动定义 RevisitEntry 覆盖，并且必须包含前两个变量
} RevisitEntry;
#endif


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

    /* 🔥 新增：函数指针（避免虚函数/分支） */
    PyObject* (*get_next)(PyObject* node);
} SafeIter;

/* 声明 utarray 的元素类型（用于 utarray 内部） */
static UT_icd RevisitEntry_icd = {sizeof(RevisitEntry), NULL, NULL, NULL};

/* 函数声明 */
void safe_iter_init(SafeIter* it);
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