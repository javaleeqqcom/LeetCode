#ifndef CONTAINER_H
#define CONTAINER_H

#include <Python.h>
#include "utarray.h"
#include "bigint_vid.h"

/* ================= IterNode ================= */
// IterNode 必须在引用前定义

/* utarray descriptor */
extern UT_icd IterNode_icd;

/* ================= Container Ops ================= */

typedef struct ContainerOps {
    void (*push)(void* ctx, const IterNode* val);
    int  (*pop)(void* ctx, IterNode* out);  // return 0 if empty
    int  (*empty)(void* ctx);
    void (*free)(void* ctx);
} ContainerOps;

/* ================= Container ================= */

typedef struct {
    void* ctx;
    ContainerOps ops;
} Container;

/* ================= API ================= */

/* stack */
int container_init_stack(Container* c);

/* queue（双 utarray 实现） */
int container_init_queue(Container* c);

/* 通用释放 */
void container_free(Container* c);

// --------------------- UT_array 迭代器 --------------------
// 用于 Cython 迭代返回的包装结构
typedef struct {
    Py_ssize_t index;
    void* obj;
} IterResult;

// 迭代状态
typedef struct {
    UT_array* arr;
    void* p;        // utarray 内部指针
    Py_ssize_t i;   // 当前索引
} UT_ArrayIter;

// 初始化迭代器
static inline UT_ArrayIter utarray_iter_make(UT_array* arr) {
    UT_ArrayIter iter = {arr, NULL, 0};
    return iter;
}

// 迭代核心：模拟 Python 的 next()
static inline unsigned char utarray_iter_next(UT_ArrayIter* iter, IterResult* out) {
    iter->p = utarray_next(iter->arr, iter->p);
    if (!iter->p) return 0;
    
    out->index = iter->i++;
    out->obj = iter->p;
    return 1;
}

// 通用 utarray_free
static inline void utarray_free_arr(UT_array* arr){
    utarray_free(arr);
}

// 访问器：Python 的 __getitem__
static inline void* utarray_getitem(UT_array* arr, Py_ssize_t index) {
    return utarray_eltptr(arr, index);
}

// 访问器：Python 的 __len__
static inline Py_ssize_t utarray_get_len(const UT_array* arr) {
    return (arr ? (Py_ssize_t)utarray_len(arr) : 0);
}

#endif