# json_test(directed).py
"""
定向序列化测试：仅对基础类型叶子数组实现单向压缩（序列化时单行，反序列化为普通列表）
核心思想：自动检测叶子数组 → 包装为LeafList → 序列化时替换为紧凑字符串 → 反序列化时自然还原为列表
"""
import json
import uuid
from typing import Any, Dict, List, Tuple, Union

class LeafList:
    """纯包装类：不继承list，确保JSON库触发default处理"""
    __slots__ = ('lst',)
    def __init__(self, lst: List[Any]):
        self.lst = lst

def _is_leaf_list(obj: Any) -> bool:
    """精准判断：仅当列表所有元素均为基础类型（含None）时返回True"""
    return isinstance(obj, list) and all(
        isinstance(x, (int, float, str, bool, type(None))) for x in obj
    )

def wrap_leaf_lists(obj: Any) -> Any:
    """递归包装：自动将所有基础类型叶子数组替换为LeafList（精简单函数实现）"""
    if isinstance(obj, list):
        return LeafList(obj) if _is_leaf_list(obj) else [wrap_leaf_lists(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: wrap_leaf_lists(v) for k, v in obj.items()}
    return obj

def _preprocess(obj: Any) -> Tuple[Any, Dict[str, str]]:
    """预处理：将LeafList替换为唯一标记，并记录映射（标记 → 紧凑JSON字符串）"""
    if isinstance(obj, LeafList):
        marker = f"__LL_{uuid.uuid4().hex}__"
        return marker, {marker: json.dumps(obj.lst, ensure_ascii=False)}
    elif isinstance(obj, dict):
        new_d, maps = {}, {}
        for k, v in obj.items():
            nv, nm = _preprocess(v)
            new_d[k] = nv  # 修正：明确赋值
            maps.update(nm)
        return new_d, maps
    elif isinstance(obj, list):
        new_l, maps = [], {}
        for item in obj:
            ni, nm = _preprocess(item)
            new_l.append(ni)
            maps.update(nm)
        return new_l, maps
    return obj, {}

def dumps_compact_leafs(obj: Any, **kwargs) -> str:
    """定向序列化核心：自动包装 → 标记替换 → 精准替换为紧凑数组"""
    wrapped = wrap_leaf_lists(obj)
    preprocessed, mappings = _preprocess(wrapped)
    json_str = json.dumps(preprocessed, **kwargs)
    
    # 安全替换：使用json.dumps确保标记字符串的精确匹配（含转义）
    for marker, compact_arr in mappings.items():
        json_str = json_str.replace(json.dumps(marker), compact_arr)
    return json_str

# ============ 测试用例 ============
def test_directed_serialization():
    test_data = {
        "short_int": [1, 2, 3],
        "long_int": list(range(50)),
        "str_arr": ["apple", "banana", "cherry"],
        "mixed_prim": [1, "text", None, True, 3.14, False],
        "nested": {
            "inner_leaf": [10, 20, 30],
            "inner_non_leaf": [{"a": 1}, {"b": [4, 5]}]  # 内含嵌套，不应压缩
        },
        "edge_cases": {
            "empty": [],
            "all_none": [None, None, None],
            "single": [42]
        },
        "non_leaf_preserved": [
            {"name": "item1", "tags": ["x", "y"]},
            {"name": "item2"}
        ]
    }
    
    json_output = dumps_compact_leafs(test_data, indent=2, ensure_ascii=False)
    print("=" * 60)
    print("生成的JSON（叶子数组单行，结构保留缩进）:")
    print("=" * 60)
    print(json_output)
    print("=" * 60)
    
    # 验证1：反序列化后数据完全一致
    loaded = json.loads(json_output)
    assert loaded == test_data, "反序列化数据不一致！"
    print("✓ 验证1：反序列化数据与原始数据完全一致")
    
    # 验证2：叶子数组在JSON中为单行（无内部换行）
    leaf_keys = ["short_int", "long_int", "str_arr", "inner_leaf", "empty", "all_none", "single", "tags"]
    for line in json_output.split('\n'):
        for key in leaf_keys:
            if f'"{key}":' in line and '[' in line:
                assert line.strip().endswith(']') or line.count('[') == line.count(']'), \
                    f"叶子数组'{key}'应单行: {line.strip()}"
    print("✓ 验证2：所有叶子数组在JSON中均为单行")
    
    # 验证3：非叶子结构保留缩进（多行）
    assert '"non_leaf_preserved": [' in json_output
    assert '    {' in json_output  # 缩进存在
    print("✓ 验证3：非叶子结构保留缩进格式")
    
    # 验证4：长数组无换行
    long_line = [l for l in json_output.split('\n') if '"long_int":' in l][0]
    assert '\n' not in long_line and '48, 49]' in long_line, "长数组应完整单行"
    print("✓ 验证4：长数组（50元素）完整单行，无换行")
    
    print("\n✅ 所有测试通过！定向序列化方案验证成功")
    print("💡 核心优势：")
    print("   • 序列化：叶子数组单行（人工友好），结构保留缩进")
    print("   • 反序列化：JSON库自然解析为普通列表（零成本）")
    print("   • 无侵入：不修改原始数据，不依赖第三方库")
    print("   • 安全：UUID标记避免冲突，精确字符串替换")

if __name__ == "__main__":
    test_directed_serialization()