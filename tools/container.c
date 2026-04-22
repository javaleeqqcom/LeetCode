#include "container.h"
#include <stdlib.h>
#include <string.h>

UT_icd IterNode_icd = {
    sizeof(IterNode),
    NULL,   // init
    NULL,   // copy
    NULL    // dtor
};

/* 声明 utarray 的元素类型（用于 utarray 内部） */
static UT_icd RevisitEntry_icd = {sizeof(RevisitEntry), NULL, NULL, NULL};

#ifndef IterNode
typedef struct {
    PyObject* node;
    // 树节点才会用到的部分
    int checked;
    BigInt vid;   
} IterNode;
#endif

// ------------------ STACK 实现 ------------------
typedef struct {
    UT_array arr;
} StackCtx;

static void stack_push(void* ctx, const IterNode* val) {
    utarray_push_back(&((StackCtx*)ctx)->arr, val);
}

static int stack_pop(void* ctx, IterNode* out) {
    StackCtx* s = (StackCtx*)ctx;
    IterNode* last = (IterNode*)utarray_back(&s->arr);
    if (!last) return 0;
    if (out) *out = *last; // 允许 out 为 NULL 仅做弹出
    utarray_pop_back(&s->arr); // 相比 resize 语义更明确
    return 1;
}

static int stack_empty(void* ctx) {
    return utarray_len(&((StackCtx*)ctx)->arr) == 0;
}

static void stack_free(void* ctx) {
    utarray_done(&((StackCtx*)ctx)->arr);
    free(ctx);
}

int container_init_stack(Container* c) {
    StackCtx* ctx = (StackCtx*)malloc(sizeof(StackCtx));
    if (!ctx) return 0;
    utarray_init(&ctx->arr, &IterNode_icd);
    c->ctx = ctx;
    c->ops = (ContainerOps){stack_push, stack_pop, stack_empty, stack_free};
    return 1;
}

// ------------------ QUEUE 高效版 ------------------
typedef struct {
    UT_array push_arr;
    UT_array pop_arr;
    size_t pop_front; 
} QueueCtx;

static void queue_refill(QueueCtx* q) {
    size_t n = utarray_len(&q->push_arr);
    if (n == 0) return;

    /* 1. 彻底销毁当前的 pop_arr 内部内存（因为它已消费完） */
    utarray_done(&q->pop_arr);

    /* 2. O(1) 精髓：直接通过结构体拷贝接管 push_arr 的底层指针和状态 */
    // 此时 pop_arr 指向了 push_arr 的内存，容量和长度完全同步
    q->pop_arr = q->push_arr; 

    /* 3. 重置游标 */
    q->pop_front = 0;

    /* 4. 重新初始化 push_arr (不再关联刚才的内存) */
    // 注意：不能对 push_arr 调用 done，否则会释放刚才给 pop_arr 的内存
    utarray_init(&q->push_arr, &IterNode_icd);
    
    /* 5. 预分配 2n 空间 */
    utarray_reserve(&q->push_arr, n * 2);
}


static void queue_push(void* ctx, const IterNode* val) {
    utarray_push_back(&((QueueCtx*)ctx)->push_arr, val);
}

static int queue_pop(void* ctx, IterNode* out) {
    QueueCtx* q = (QueueCtx*)ctx;
    // 如果 pop_arr 消费完，尝试 refill
    if (q->pop_front >= utarray_len(&q->pop_arr)) {
        queue_refill(q);
    }
    
    // refill 后再次检查是否有数据
    if (q->pop_front >= utarray_len(&q->pop_arr)) return 0;

    IterNode* e = (IterNode*)utarray_eltptr(&q->pop_arr, q->pop_front);
    if (out) *out = *e;
    q->pop_front++;
    return 1;
}

static int queue_empty(void* ctx) {
    QueueCtx* q = (QueueCtx*)ctx;
    // 关键：push 数组为空且 pop 数组已读完才是真的空
    return utarray_len(&q->push_arr) == 0 && (q->pop_front >= utarray_len(&q->pop_arr));
}

static void queue_free(void* ctx) {
    QueueCtx* q = (QueueCtx*)ctx;
    utarray_done(&q->push_arr);
    utarray_done(&q->pop_arr);
    free(q);
}

int container_init_queue(Container* c) {
    QueueCtx* ctx = (QueueCtx*)malloc(sizeof(QueueCtx));
    if (!ctx) return 0;
    utarray_init(&ctx->push_arr, &IterNode_icd);
    utarray_init(&ctx->pop_arr, &IterNode_icd);
    ctx->pop_front = 0;
    c->ctx = ctx;
    c->ops = (ContainerOps){queue_push, queue_pop, queue_empty, queue_free};
    return 1;
}

void container_free(Container* c) {
    if (c && c->ops.free && c->ctx) {
        c->ops.free(c->ctx);
        c->ctx = NULL;
    }
}


