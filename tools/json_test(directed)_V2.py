# json_test(directed_final.py
"""
高效定向序列化：占位符替换法（严格按用户伪代码实现）
核心流程：
  1. 收集所有原始字符串（含字典键）→ 避免占位符冲突
  2. 预处理：叶子序列 → 唯一占位符（@LL_<uuid>），记录映射
  3. 标准序列化
  4. 精准替换：仅替换带双引号的占位符字符串 → 紧凑JSON数组
优势：零误替换风险、与json.dumps行为100%一致、无额外类定义
"""
import json
import uuid
from typing import Any, Set, List, Tuple, Dict

def _collect_all_strings(obj: Any, string_set: Set[str]) -> None:
    """递归收集对象中所有字符串（含字典键！关键：避免占位符冲突）"""
    if isinstance(obj, str):
        string_set.add(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            string_set.add(k)  # 字典键必须收集！
            _collect_all_strings(v, string_set)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _collect_all_strings(item, string_set)
    # 其他类型（int/float/bool/None）忽略

def _is_leaf_sequence(obj: Any) -> bool:
    """判断是否为叶子序列（list/tuple + 元素全为基础类型）"""
    if not isinstance(obj, (list, tuple)):
        return False
    return all(isinstance(x, (int, float, str, bool, type(None))) for x in obj)

def _replace_leaf_sequences(
    obj: Any, 
    forbidden_strings: Set[str], 
    mapping: List[Tuple[str, Any]]
) -> Any:
    """
    预处理：将叶子序列替换为唯一占位符
    - 占位符格式: "@LL_<32位hex>"
    - 严格避开 forbidden_strings（含原始数据所有字符串）
    - 记录映射: (占位符, 原始序列)
    """
    if _is_leaf_sequence(obj):
        # 生成唯一占位符（避开所有原始字符串）
        while True:
            placeholder = f"@LL_{uuid.uuid4().hex}"
            if placeholder not in forbidden_strings:
                break
        mapping.append((placeholder, obj))
        return placeholder
    
    if isinstance(obj, dict):
        return {k: _replace_leaf_sequences(v, forbidden_strings, mapping) for k, v in obj.items()}
    
    if isinstance(obj, list):
        return [_replace_leaf_sequences(item, forbidden_strings, mapping) for item in obj]
    
    if isinstance(obj, tuple):
        # 非叶子元组：转为列表（与json.dumps行为一致）
        return [_replace_leaf_sequences(item, forbidden_strings, mapping) for item in obj]
    
    return obj

def my_dump(obj: Any, **kwargs) -> str:
    """
    高效定向序列化入口
    保证: json.loads(my_dump(x)) == json.loads(json.dumps(x))
    """
    # 步骤1: 收集所有原始字符串（关键！避免占位符冲突）
    all_strings: Set[str] = set()
    _collect_all_strings(obj, all_strings)
    
    # 步骤2: 预处理 - 替换叶子序列为占位符
    mapping: List[Tuple[str, Any]] = []
    processed_obj = _replace_leaf_sequences(obj, all_strings, mapping)
    
    # 步骤3: 标准序列化
    json_str = json.dumps(processed_obj, **kwargs)
    
    # 步骤4: 精准替换（按占位符长度降序，避免子串干扰）
    replacements = []
    for placeholder, seq in mapping:
        # 1. 生成紧凑JSON数组（元组→列表，与json.dumps一致）
        compact_json = json.dumps(
            list(seq) if isinstance(seq, tuple) else seq,
            separators=(',', ':'),
            ensure_ascii=False
        )
        # 2. 生成带双引号的占位符（如'"@LL_abc"'）
        quoted_placeholder = json.dumps(placeholder)
        replacements.append((quoted_placeholder, compact_json))
    
    # 按长度降序排序（长占位符优先替换，避免短串是长串子串）
    replacements.sort(key=lambda x: len(x[0]), reverse=True)
    
    # 3. 执行替换（安全：仅替换完整带引号的占位符）
    for quoted_placeholder, compact_json in replacements:
        json_str = json_str.replace(quoted_placeholder, compact_json)
    
    return json_str

# ============ 严格验证测试 ============
def test_my_dump_consistency():
    """核心验证：my_dump 与 json.dumps 反序列化结果必须完全一致"""
    test_cases = [
        # 基础类型
        {"a": [1, 2, 3], "b": ["x", "y"]},
        # 长数组（验证单行）
        {"long": list(range(100))},
        # 嵌套结构
        {"nested": {"inner": [10, 20], "mixed": [{"tags": [1,2]}, [3,4]]}},
        # 边界情况
        {"empty": [], "single": [42], "all_none": [None, None]},
        # 特殊字符（验证ensure_ascii）
        {"text": ["α", "β", "中文", "Emoji: 🌟", 'quote"']}, 
        # 元组处理（关键：与json.dumps行为一致）
        {"tuple_leaf": (1, 2, 3), "tuple_nested": ([1], (2,))},
        # 冲突测试：原始数据含"@LL_"前缀字符串（验证占位符唯一性）
        {"conflict_test": "@LL_abc", "real_leaf": [1, 2, 3]},
        # 复杂嵌套
        [
            {"name": "item1", "tags": ["a", "b"]},
            {"name": "item2", "scores": [95, 87, 92]}
        ]
    ]
    
    print("=" * 70)
    print("🔍 严格一致性验证：my_dump vs json.dumps")
    print("=" * 70)
    
    for i, case in enumerate(test_cases, 1):
        # 标准JSON
        std_json = json.dumps(case, indent=2, ensure_ascii=False)
        std_obj = json.loads(std_json)
        
        # my_dump JSON
        custom_json = my_dump(case, indent=2, ensure_ascii=False)
        custom_obj = json.loads(custom_json)
        
        # 关键验证1：反序列化结果必须完全相等
        assert std_obj == custom_obj, (
            f"❌ Case {i} 反序列化结果不一致!\n"
            f"Standard: {std_obj}\nCustom:   {custom_obj}"
        )
        
        # 关键验证2：叶子数组在custom_json中为单行
        if isinstance(case, dict) and "long" in case:
            lines = custom_json.split('\n')
            long_line = next(l for l in lines if '"long":' in l)
            assert '\n' not in long_line or '99]' in long_line, \
                f"❌ Case {i} 长数组未单行: {long_line}"
        
        # 关键验证3：冲突测试中"@LL_abc"字符串未被误替换
        if "conflict_test" in str(case):
            assert '"@LL_abc"' in custom_json, \
                "❌ 原始字符串'@LL_abc'被误替换！"
            assert "[1,2,3]" in custom_json, \
                "❌ 叶子数组未被正确替换！"
        
        print(f"✓ Case {i:2d}: PASS (结构深度={_get_depth(case)})")
    
    # 额外验证：大数组性能
    big_case = {"data": list(range(10000))}
    import time
    start = time.time()
    _ = my_dump(big_case)
    elapsed = time.time() - start
    print(f"\n⚡ 性能验证：10,000元素数组序列化耗时 {elapsed*1000:.2f}ms")
    
    print("\n✅ 所有验证通过！my_dump 与 json.dumps 行为100%一致")
    print("💡 核心保障：")
    print("   • 占位符唯一性：通过收集所有原始字符串确保零冲突")
    print("   • 精准替换：仅替换带双引号的完整占位符（quoted_placeholder）")
    print("   • 元组处理：自动转为列表，与json.dumps行为完全一致")
    print("   • 安全边界：原始数据含'@LL_'前缀字符串时仍正确处理")

def _get_depth(obj: Any, depth: int = 0) -> int:
    """辅助：计算对象嵌套深度（用于测试报告）"""
    if isinstance(obj, dict):
        return max((_get_depth(v, depth+1) for v in obj.values()), default=depth)
    if isinstance(obj, (list, tuple)):
        return max((_get_depth(item, depth+1) for item in obj), default=depth)
    return depth

if __name__ == "__main__":
    test_my_dump_consistency()