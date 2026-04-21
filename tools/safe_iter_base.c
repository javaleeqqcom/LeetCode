#include "safe_iter_base.h"
#include <stdlib.h>

void safe_iter_init(SafeIter* it, UT_icd *RevisitEntry_icd) {
    it->seen = NULL;
    utarray_new(it->revisit, RevisitEntry_icd);

    it->repeat_num = 0;
    it->cur = null_entry();
}

void safe_iter_free(SafeIter* it) {
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
    if(it->cur.node){
        Py_DECREF(it->cur.node);
        it->cur = null_entry();
    }
}

size_t safe_iter_check_safe(SafeIter* it, void* entry_ele) {
    PyObject* node = ((BaseEntry*)entry_ele)->node;
    if (_is_null(node)) {
        return (size_t)-1;
    }

    SeenEntry* entry = NULL;
    HASH_FIND_PTR(it->seen, &node, entry);

    if (entry) {
        // 🔁 重复
        size_t first_idx = entry->uf_index;
        
        // 先将 entry_ele 按 it->revisit 元素大小复制 push 进 it->revisit
        utarray_push_back(it->revisit, entry_ele);
        // 然后修改其刚插入尾元素的 uf_index，指向首次出现 node 的下标 first_idx
        safe_iter_last_revisit(it)->uf_index = first_idx;

        RevisitEntry* first = safe_iter_get_revisit(it, first_idx);

        if (first->uf_index == (size_t)-1) {
            first->uf_index = first_idx;
            it->repeat_num++;
        }

        return (size_t)-1;
    } else {
        // 🆕 是无重复的新节点
        size_t idx = utarray_len(it->revisit);

        // 无重复点新节点 uf_index 为 -1
        utarray_push_back(it->revisit, entry_ele);
        safe_iter_last_revisit(it)->uf_index = -1;

        entry = (SeenEntry*)malloc(sizeof(SeenEntry));
        if (!entry) {
            PyErr_NoMemory();
            return (size_t)-1;
        }

        entry->key = node;
        entry->uf_index = idx;
        Py_INCREF(node); // 先确保 _seen 持有引用计数，将来再进行抵消优化

        HASH_ADD_PTR(it->seen, key, entry);

        return idx;
    }
}

// 如下 -------- 改为 c（保持指针态，返回 RevisitEntry 而非 object，以便各类 flatten 高效处理）
RevisitEntry safe_iter_next(SafeIter* it, void (*prepare_next)(SafeIter*)) {
    RevisitEntry res = it->cur; // 先拷贝当前 cur 作为返回
    if (_is_null(res.node)) {
        return res; // 节点为空
    }
    // prepare_next 必须实现：用于准备下一个 it->cur ，需确保：
    // - 不用检查 it->cur 非空，因为 safe_iter_next 检查过了
    // - 需自行调用 _check_safe 确保查重安全
    // - 需要自行确保 it->cur 的 PyObject 引用计数安全
    prepare_next(it); 
    return res;
}

// ===== safe_iter_skip_next =====
RevisitEntry safe_iter_skip_next(SafeIter* it,
                              void (*prepare_next)(SafeIter*),
                              Py_ssize_t index
                             ) {
    if(index < 0){ return null_entry();}
    // 空或迭代次数达到Index则跳出循环（当 index == 0 时，无需迭代，取 it->cur即可）
    for (Py_ssize_t i = 0; !_is_null(it->cur.node) && i < index ; i++) {
        safe_iter_next(it, prepare_next);
    }
    return it->cur;
}

RevisitEntry* ...revisit_flatten(SafeIter it, Py_ssize_t max_len=-2):
    cdef UT_array out = []
    cdef int i = 0
    cdef PyObject node
    cdef _max_len = _limit_size(max_len)
    # 改为调用 safe_iter_next 而不是用 for 以便高效处理
    for node in it:
        out.append(node)
        i += 1
        if _max_len >= 0 and i >= _max_len:
            break
    return out

// 请实现，可用于 _string 避免 objcet 更高效的遍历
RevisitEntry* ...revisit_nodes(SafeIter* it):
    RevisitEntry* list result = 申请 it.repete_num 个
    ...
    return result;