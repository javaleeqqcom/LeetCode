#include "safe_iter_base.h"
#include <stdlib.h>

void safe_iter_init(SafeIter* it, UT_icd *RevisitEntry_icd) {
    it->seen = NULL;
    it->check_record = NULL;
    utarray_new(it->check_record, RevisitEntry_icd);

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
    if (it->check_record) {
        utarray_free(it->check_record);
        it->check_record = NULL;
    }
    // 释放当前节点引用
    if(it->cur.node){
        Py_DECREF(it->cur.node);
        it->cur = null_entry();
    }
}

// 检查 check_record 尾部节点是否重复。返回 TRUE 表示新节点（安全），FALSE 表示重复节点（不安全）。
// 副作用：更新尾部元素的 c_index；若重复，可能更新首次出现节点的 c_index 并增加 repeat_num。
BOOL safe_iter_check_safe(SafeIter* it){
    CheckEntry* entry = safe_iter_tail(it);
    PyObject* node = entry->node;

    if (_is_null(node)) {
        entry->c_index = -1;
        return FALSE;
    }

    SeenEntry* found = NULL;
    HASH_FIND_PTR(it->seen, &node, found);

    if (found) {
        // 🔁 重复
        Py_ssize_t first_idx = found->c_index;
        entry->c_index = first_idx;

        CheckEntry* first = (CheckEntry*)safe_iter_get_revisit(it, first_idx);
        if (first->c_index == -1) {
            first->c_index = first_idx;
            it->repeat_num++;
        }
        return FALSE;
    }

    // 🆕 新节点
    Py_ssize_t new_idx = utarray_len(it->check_record) - 1;
    entry->c_index = -1;

    SeenEntry* new_entry = malloc(sizeof(SeenEntry));
    if (!new_entry) {
        PyErr_NoMemory();
        return FALSE;
    }

    new_entry->key = node;
    new_entry->c_index = new_idx;

    Py_INCREF(node);
    HASH_ADD_PTR(it->seen, key, new_entry);

    return TRUE;
}

// 保持指针态，返回 CheckEntry及其派生的指针 而非 object，以便各类 flatten 高效处理
// 需要在 Cython 端中实现 prepare_next ：用于准备下一个 it->cur ，需确保：
// - 不用检查 it->cur 非空，因为 safe_iter_next 检查过了
// - 需自行调用 _check_safe 确保查重安全
// - 需要自行确保 it->cur 的 PyObject 引用计数安全
const void* safe_iter_next(SafeIter* it)
{
    if (-1 == it->cur_index) {
        return NULL;
    }
    it->prepare(it, it->ctx); 
    // 根据子类选择 CheckEntry 或其派生结构体进行恢复
    return (const void*)safe_iter_get_revisit(it,it->cur_index); 
}

// ===== safe_iter_skip_next =====
const void* safe_iter_skip_next(SafeIter* it,Py_ssize_t index) {
    if(index < 0){ return NULL;}
    // 空或迭代次数达到Index则跳出循环（当 index == 0 时，无需迭代，取 it->cur即可）
    for (Py_ssize_t i = 0; it->cur_index >= 0 && i < index ; i++) {
        it->prepare(it, it->ctx);
    }
    return it->cur_index;
}

// ===== safe_iter_flatten_entrys: 使用迭代器 it 迭代至多 max_len 次，并收集 CheckEntry 数组 =====
// 注意执行 safe_iter_flatten_entrys 会改变迭代器对象！
UT_array* safe_iter_flatten_entrys(SafeIter* it, Py_ssize_t max_len) {
    // 删除 safe_iter_flatten_entrys，因为链表可以直接从 check_record 中读取
    // 而树只需维护一个 c_index 列表即可还原
    // 可直接在 Cython 中实现对应逻辑
}

CheckEntry* safe_iter_revisit_nodes(const SafeIter* it, Py_ssize_t* out_len) {
    Py_ssize_t n = safe_iter_size(it);
    Py_ssize_t count = it->repeat_num;

    if (count == 0) {
        *out_len = 0;
        return NULL;
    }

    CheckEntry* result = (CheckEntry*)malloc(sizeof(CheckEntry) * count);
    if (!result) {
        PyErr_NoMemory();
        *out_len = 0;
        return NULL;
    }

    Py_ssize_t k = 0;
    for (Py_ssize_t i = 0; i < n; i++) {
        const CheckEntry* entry = safe_iter_get_revisit(it, i);
        if (entry->c_index == i) {
            result[k++] = *entry;
        }
    }

    *out_len = k;
    return result;
}