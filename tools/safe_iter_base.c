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

// ===== safe_iter_flatten_entrys: 使用迭代器 it 迭代至多 max_len 次，并收集 RevisitEntry 数组 =====
UT_array safe_iter_flatten_entrys(SafeIter* it, void (*prepare_next)(SafeIter*), Py_ssize_t max_len) {
    UT_array result = ... // 预分配 min(max_len, 1024) 个空间吧
    if (!result) {
        PyErr_NoMemory();
        *out_len = 0;
        return NULL;
    }

    for (size_t i = 0; i < size; i++) {
        result[i] = safe_iter_next(it, prepare_next);
    }
    // 如果实际 size 远远小于 预分配空间，看 UT_array 是否支持动态缩容，否则就算了

    return result;
}

// 请实现，可用于 _string 避免 objcet 更高效的遍历
const RevisitEntry* safe_iter_revisit_nodes(const SafeIter* it, size_t* out_len) {
    size_t n = safe_iter_size(it);
    size_t count = it->repeat_num;

    if (count == 0) {
        *out_len = 0;
        return NULL;
    }

    RevisitEntry* result = (RevisitEntry*)malloc(sizeof(RevisitEntry) * count);
    if (!result) {
        PyErr_NoMemory();
        *out_len = 0;
        return NULL;
    }

    size_t k = 0;

    for (size_t i = 0; i < n; i++) {
        const RevisitEntry* entry = safe_iter_get_revisit(it,i);

        if (entry->uf_index == i) {
            result[k++] = *entry;
        }
    }

    *out_len = k;
    return result;
}