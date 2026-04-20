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

#endif