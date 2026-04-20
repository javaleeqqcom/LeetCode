#include "safe_iter_base.h"
#include <stdlib.h>

void safe_iter_init(SafeIter* it, UT_icd *RevisitEntry_icd) {
    it->seen = NULL;
    utarray_new(it->revisit, RevisitEntry_icd);

    it->repeat_num = 0;

    it->cur = Py_None;
    Py_INCREF(Py_None);
}

void safe_iter_cleanup(SafeIter* it) {
    // 释放哈希表
    SeenEntry *entry, *tmp;
    HASH_ITER(hh, it->seen, entry, tmp) {
        Py_DECREF(entry->key);
        HASH_DEL(it->seen, entry);
        free(entry);
    }
    // 释放动态数组
    if (it->revisit) {
        utarray_free(it->revisit);
        it->revisit = NULL;
    }
    // 释放当前节点引用
    Py_DECREF(it->cur);
    it->cur = NULL;
}

size_t safe_iter_check_safe(SafeIter* it, void* entry_ele) {

    PyObject* node = it->get_node_ptr(entry_ele); // 好像可以用 (RevisitEntry*) 强转，取消掉 get_node_ptr 函数指针，节约代码

    if (node == NULL || node == Py_None) {
        return (size_t)-1;
    }

    SeenEntry* entry = NULL;
    HASH_FIND_PTR(it->seen, &node, entry);

    if (entry) {
        // 🔁 重复
        size_t first_idx = entry->index;

        it->push_revisit(it, entry_ele);

        RevisitEntry* last =
            (RevisitEntry*)utarray_back(it->revisit);

        last->uf_index = first_idx;

        RevisitEntry* first =
            (RevisitEntry*)utarray_eltptr(it->revisit, first_idx);

        if (first->uf_index == (size_t)-1) {
            first->uf_index = first_idx;
            it->repeat_num++;
        }

        return (size_t)-1;

    } else {
        // 🆕 新节点
        size_t idx = utarray_len(it->revisit);

        it->push_revisit(it, entry_ele);

        // 插入哈希表
        entry = (SeenEntry*)malloc(sizeof(SeenEntry));
        if (!entry) {
            PyErr_NoMemory();
            return (size_t)-1;
        }

        entry->key = node;
        entry->index = idx;

        Py_INCREF(node);
        HASH_ADD_PTR(it->seen, key, entry);

        return idx;
    }
}
