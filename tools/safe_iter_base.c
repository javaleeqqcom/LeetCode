#include "safe_iter_base.h"
#include <stdlib.h>

void safe_iter_init(SafeIter* it, UT_icd *RevisitEntry_icd) {
    it->seen = NULL;
    it->revisit = NULL;
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

// 检查 entry_ele 是否安全，如果是则返回其新插入在 revisit 中的索引，否则返回 -1（包括空节点、重复节点、无法插入等情况）
Py_ssize_t safe_iter_check_safe(SafeIter* it, const RevisitEntry* entry_ele) {
    PyObject* node = entry_ele->node;
    if (_is_null(node)) {
        return -1;
    }

    SeenEntry* entry = NULL;
    HASH_FIND_PTR(it->seen, &node, entry);

    if (entry) {
        // 🔁 重复：返回指向重复节点的索引
        Py_ssize_t first_idx = entry->uf_index;

        // 先将 entry_ele 按 it->revisit 元素大小复制 push 进 it->revisit
        utarray_push_back(it->revisit, (const void*)entry_ele); // 此处 entry_ele 实际拷贝字节允许超过 sizeof(RevisitEntry) ，以
        // 然后修改其刚插入尾元素的 uf_index，指向首次出现 node 的下标 first_idx
        safe_iter_last_revisit(it)->uf_index = first_idx;

        RevisitEntry* first = safe_iter_get_revisit(it, first_idx);

        if (first->uf_index == -1) {
            first->uf_index = first_idx;
            it->repeat_num++;
        }

        return (size_t)-1;
    } else {
        // 🆕 是无重复的新节点
        Py_ssize_t new_idx = utarray_len(it->revisit);

        // 无重复点新节点 uf_index 为 -1
        utarray_push_back(it->revisit, (const void*)entry_ele);
        safe_iter_last_revisit(it)->uf_index = -1;

        entry = (SeenEntry*)malloc(sizeof(SeenEntry));
        if (!entry) {
            PyErr_NoMemory();
            return -1;
        }

        entry->key = node;
        entry->uf_index = new_idx;
        Py_INCREF(node); // 先确保 _seen 持有引用计数，将来再进行抵消优化

        HASH_ADD_PTR(it->seen, key, entry);

        return new_idx;
    }
}

// 保持指针态，返回 RevisitEntry 而非 object，以便各类 flatten 高效处理
// 需要在 Cython 端中实现 prepare_next ：用于准备下一个 it->cur ，需确保：
// - 不用检查 it->cur 非空，因为 safe_iter_next 检查过了
// - 需自行调用 _check_safe 确保查重安全
// - 需要自行确保 it->cur 的 PyObject 引用计数安全
RevisitEntry safe_iter_next(SafeIter* it)
{
    RevisitEntry res = it->cur;
    if (_is_null(res.node)) {
        return res;
    }
    it->prepare(it, it->ctx); 
    // ⚠️ 返回的 node 不增加引用计数，仅在当前迭代周期内有效
    return res; 
}

// ===== safe_iter_skip_next =====
RevisitEntry safe_iter_skip_next(SafeIter* it,Py_ssize_t index) {
    if(index < 0){ return null_entry();}
    // 空或迭代次数达到Index则跳出循环（当 index == 0 时，无需迭代，取 it->cur即可）
    for (Py_ssize_t i = 0; !_is_null(it->cur.node) && i < index ; i++) {
        safe_iter_next(it);
    }
    return it->cur;
}

// ===== safe_iter_flatten_entrys: 使用迭代器 it 迭代至多 max_len 次，并收集 RevisitEntry 数组 =====
// 注意执行 safe_iter_flatten_entrys 会改变迭代器对象！
UT_array* safe_iter_flatten_entrys(SafeIter* it, Py_ssize_t max_len) {
    UT_array* result;
    UT_icd icd = { sizeof(RevisitEntry), NULL, NULL, NULL };

    utarray_new(result, &icd);
    if (!result) {
        PyErr_NoMemory();
        return NULL;
    }

    Py_ssize_t limit = _limit_size(max_len);

    for (Py_ssize_t i = 0; i < limit; i++) {
        if (_is_null(it->cur.node)) break;

        utarray_push_back(result, &it->cur);
        it->prepare(it,it->ctx);
    }

    return result;
}

RevisitEntry* safe_iter_revisit_nodes(const SafeIter* it, Py_ssize_t* out_len) {
    Py_ssize_t n = safe_iter_size(it);
    Py_ssize_t count = it->repeat_num;

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

    Py_ssize_t k = 0;
    for (Py_ssize_t i = 0; i < n; i++) {
        const RevisitEntry* entry = safe_iter_get_revisit(it, i);
        if (entry->uf_index == i) {
            result[k++] = *entry;
        }
    }

    *out_len = k;
    return result;
}