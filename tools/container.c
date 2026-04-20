#include "container.h"
#include <stdlib.h>
#include <string.h>

UT_icd IterNode_icd = {
    sizeof(IterNode),
    NULL,   // init
    NULL,   // copy
    NULL    // dtor
};

#ifndef IterNode
typedef struct {
    PyObject* node;
    // 树节点才会用到的部分
    // int checked;
    // BigInt vid;   
} IterNode;
#endif
// ------------ STACK 实现（utarray）-----------------
typedef struct {
    UT_array* arr;
} StackCtx;
static void stack_push(void* ctx, const IterNode* val) {
    StackCtx* s = (StackCtx*)ctx;
    utarray_push_back(s->arr, val);
}
static int stack_pop(void* ctx, IterNode* out) {
    StackCtx* s = (StackCtx*)ctx;

    size_t len = utarray_len(s->arr);
    if (len == 0) return 0;

    IterNode* last = (IterNode*)utarray_eltptr(s->arr, len - 1);
    *out = *last;

    utarray_resize(s->arr, len - 1);
    return 1;
}
static int stack_empty(void* ctx) {
    StackCtx* s = (StackCtx*)ctx;
    return utarray_len(s->arr) == 0;
}
static void stack_free(void* ctx) {
    StackCtx* s = (StackCtx*)ctx;
    if (s->arr) utarray_free(s->arr);
    free(s);
}
int container_init_stack(Container* c) {
    StackCtx* ctx = (StackCtx*)malloc(sizeof(StackCtx));
    if (!ctx) return 0;

    utarray_new(ctx->arr, &IterNode_icd);
    if (!ctx->arr) {
        free(ctx);
        return 0;
    }

    c->ctx = ctx;
    c->ops.push = stack_push;
    c->ops.pop = stack_pop;
    c->ops.empty = stack_empty;
    c->ops.free = stack_free;

    return 1;
}

// ------------------ QUEUE “双数组优化版（非双stack）” ------------------
typedef struct {
    UT_array* push_arr;
    UT_array* pop_arr;
    size_t pop_front;   // 当前 pop 起点
} QueueCtx;
static void queue_refill(QueueCtx* q) {
    size_t n = utarray_len(q->push_arr);
    if (n == 0) return;

    /* 释放旧 pop_arr（已经被消费完） */
    if (q->pop_arr) {
        utarray_free(q->pop_arr);
    }

    /* 直接接管 push_arr */
    q->pop_arr = q->push_arr;
    q->pop_front = 0;

    /* 新建 push_arr，并预分配 2n */
    utarray_new(q->push_arr, &IterNode_icd);
    utarray_reserve(q->push_arr, n * 2);
}
static void queue_push(void* ctx, const IterNode* val) {
    QueueCtx* q = (QueueCtx*)ctx;
    utarray_push_back(q->push_arr, val);
}
static int queue_pop(void* ctx, IterNode* out) {
    QueueCtx* q = (QueueCtx*)ctx;

    if (!q->pop_arr || q->pop_front >= utarray_len(q->pop_arr)) {
        queue_refill(q);
    }

    if (!q->pop_arr) return 0;

    size_t len = utarray_len(q->pop_arr);
    if (q->pop_front >= len) return 0;

    IterNode* e = (IterNode*)utarray_eltptr(q->pop_arr, q->pop_front);
    *out = *e;

    q->pop_front++;
    return 1;
}
static int queue_empty(void* ctx) {
    QueueCtx* q = (QueueCtx*)ctx;
    return utarray_len(q->push_arr) == 0 &&
           utarray_len(q->pop_arr) == 0;
}
static void queue_free(void* ctx) {
    QueueCtx* q = (QueueCtx*)ctx;

    if (q->push_arr) utarray_free(q->push_arr);
    if (q->pop_arr) utarray_free(q->pop_arr);

    free(q);
}
int container_init_queue(Container* c) {
    QueueCtx* ctx = (QueueCtx*)malloc(sizeof(QueueCtx));
    if (!ctx) return 0;

    ctx->push_arr = NULL;
    ctx->pop_arr  = NULL;

    utarray_new(ctx->push_arr, &IterNode_icd);
    utarray_new(ctx->pop_arr,  &IterNode_icd);

    if (!ctx->push_arr || !ctx->pop_arr) {
        if (ctx->push_arr) utarray_free(ctx->push_arr);
        if (ctx->pop_arr) utarray_free(ctx->pop_arr);
        free(ctx);
        return 0;
    }

    c->ctx = ctx;
    c->ops.push = queue_push;
    c->ops.pop = queue_pop;
    c->ops.empty = queue_empty;
    c->ops.free = queue_free;

    return 1;
}

// ------------- 统一释放接口 ----------------------
void container_free(Container* c) {
    if (c->ops.free && c->ctx) {
        c->ops.free(c->ctx);
    }
    c->ctx = NULL;
}
