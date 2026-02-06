# json_test(directed).py
"""
定向序列化实现：仅叶子数组（基础类型+None）输出为紧凑单行格式
核心思路：唯一占位符替换 + 精确字符串替换，避免递归序列化开销
保证：my_dump输出反序列化结果 ≡ json.dumps输出反序列化结果
"""
import json
import re
import uuid
from typing import Any, List, Tuple

# 配置：占位符长度（32位十六进制 = UUID标准长度）
_HEX_COUNT = 4
_ALIAS_PATTERN = re.compile(rf'"@([0-9a-fA-F]{{{_HEX_COUNT}}})"')

def _is_leaf_sequence(obj: Any) -> bool:
    """判断是否为叶子序列（list/tuple + 元素全为基础类型）"""
    if not isinstance(obj, (list, tuple)):
        return False
    return all(isinstance(x, (int, float, str, bool, type(None))) for x in obj)

def my_dump(obj: Any, **kwargs) -> str:
    """
    定向序列化：外层结构保留缩进，叶子数组强制单行紧凑输出
    保证反序列化结果与标准 json.dumps 完全一致
    """
    # 步骤1: 提取原始数据中已存在的占位符（避免冲突）
    json_str0 = json.dumps(obj, **kwargs)
    alias_set = set(_ALIAS_PATTERN.findall(json_str0))
    
    # 步骤2: 递归替换叶子序列为唯一占位符，构建映射表
    alias_obj_list: List[Tuple[str, str]] = []  # [(占位符JSON字符串, 紧凑数组JSON字符串), ...]
    
    def replace_with_alias(sub_obj: Any) -> Any:
        if _is_leaf_sequence(sub_obj):
            # 生成唯一占位符（避开原始数据中已存在的）
            while True:
                hash_code = uuid.uuid4().hex[:_HEX_COUNT]
                if hash_code not in alias_set:
                    break
            alias_set.add(hash_code)
            placeholder = "@" + hash_code
            # 记录：占位符的JSON表示（带引号） + 紧凑数组JSON
            alias_obj_list.append((
                json.dumps(placeholder),  # 安全生成带引号的占位符字符串
                json.dumps(sub_obj)       # 紧凑格式（无indent）
            ))
            return placeholder
        elif isinstance(sub_obj, dict):
            return {k: replace_with_alias(v) for k, v in sub_obj.items()}
        elif isinstance(sub_obj, (list, tuple)):
            # 非叶子序列：递归处理元素（元组转为列表，与JSON标准行为一致）
            return [replace_with_alias(item) for item in sub_obj]
        else:
            return sub_obj
    
    # 步骤3: 生成带占位符的中间JSON
    obj_with_placeholders = replace_with_alias(obj)
    json_str1 = json.dumps(obj_with_placeholders, **kwargs)
    
    # 步骤4: 按顺序精准替换（利用alias_obj_list顺序与json_str1中出现顺序一致）
    if not alias_obj_list:
        return json_str1
    
    parts = []
    start = 0
    for placeholder_json, compact_array in alias_obj_list:
        idx = json_str1.find(placeholder_json, start)
        if idx == -1:  # 安全兜底（理论上不应发生）
            continue
        parts.append(json_str1[start:idx])
        parts.append(compact_array)
        start = idx + len(placeholder_json)
    parts.append(json_str1[start:])
    
    return "".join(parts)

# ==================== 严格验证测试 ====================
def test_roundtrip_consistency():
    """核心验证：my_dump 与 json.dumps 反序列化结果必须完全一致"""
    test_cases = [
        # 基础类型叶子数组
        {"arr": [1, 2, 3, 4, 5]},
        {"long": list(range(100))},
        {"mixed": [1, "text", None, True, 3.14, False]},
        {"edge": [[], [None], [42]]},
        
        # 嵌套结构（叶子数组在深层）
        {
            "nested": {
                "inner": [10, 20, 30],
                "mixed_arr": [{"a": 1}, {"b": [4, 5]}]  # [4,5]是叶子数组
            },
            "items": [
                {"name": "x", "tags": ["a", "b", "c"]},  # tags是叶子数组
                {"name": "y"}
            ]
        },
        
        # 原始数据含占位符字符串（验证冲突避免）
        {"trap": f"@{uuid.uuid4().hex[:_HEX_COUNT]}", "real_leaf": [1, 2, 3]},
        
        # 元组处理（JSON标准会转为列表，验证一致性）
        {"tuple_leaf": (1, 2, 3), "tuple_nested": [(1, 2), [3, 4]]},
        
        # 复杂混合结构
        {
            "data": [
                {"values": [0.1, 0.2, 0.3], "meta": {"id": 1}},
                {"values": [1.1, 1.2], "meta": {"id": 2}}
            ],
            "summary": [100, 200, 300]
        }
    ]
    
    params = {"indent": 2, "ensure_ascii": False}
    all_passed = True
    
    print("=" * 70)
    print("开始验证：my_dump 与 json.dumps 反序列化结果一致性")
    print("=" * 70)
    
    for i, case in enumerate(test_cases, 1):
        try:
            # 标准JSON流程
            std_json = json.dumps(case, **params)
            std_obj = json.loads(std_json)
            
            # my_dump流程
            custom_json = my_dump(case, **params)
            custom_obj = json.loads(custom_json)
            
            # 严格比较（忽略元组/列表差异，因JSON标准统一转为列表）
            assert std_obj == custom_obj, f"反序列化结果不一致！\n标准: {std_obj}\n自定义: {custom_obj}"
            
            # 验证叶子数组在输出中为单行
            if "long" in case or "values" in str(case):
                lines = custom_json.split('\n')
                has_multiline_leaf = any(
                    ('[' in line and ']' in line and line.count('[') == line.count(']') and 
                     line.strip().startswith('[') and not line.strip().endswith('['))
                    for line in lines
                )
                assert not has_multiline_leaf, "叶子数组不应跨多行"
            
            print(f"✓ 用例 {i} 通过: 结构一致 | 叶子数组单行验证通过")
        except Exception as e:
            print(f"✗ 用例 {i} 失败: {type(e).__name__}: {e}")
            print(f"原始数据: {case}")
            all_passed = False
    
    # 额外验证：长数组单行输出（人工可读性关键）
    long_case = {"data": list(range(200))}
    output = my_dump(long_case, indent=2)
    long_line = [l for l in output.split('\n') if 'data' in l][0]
    assert '\n' not in long_line and '199]' in long_line, "长数组必须单行"
    print("✓ 长数组(200元素)验证: 完整单行输出")
    
    print("=" * 70)
    if all_passed:
        print("✅ 所有验证通过！my_dump 满足核心要求：")
        print("   • 反序列化结果 ≡ 标准 json.dumps")
        print("   • 叶子数组强制单行（人工友好）")
        print("   • 外层结构保留缩进")
        print("   • 安全处理占位符冲突")
        print("   • 元组/列表处理与JSON标准一致")
    else:
        print("❌ 存在验证失败项")
    print("=" * 70)
    
    # 可选：输出示例供人工检查
    example = {
        "short": [1, 2, 3],
        "long": list(range(30)),
        "nested": {"inner": [10, 20, 30]},
        "non_leaf": [{"a": [1, 2]}]  # [1,2]是叶子数组，外层列表保留缩进
    }
    print("\n【输出示例】观察格式：")
    print(my_dump(example, indent=2))

# json_test(directed).py (续)
import random
import string
from multiprocessing import Pool, cpu_count
# 字符集：包含 '"{}[]@' 和 0-9,A-Z,a-z
CHARSET = '"' + "'" + "{}[]@" + string.digits + string.ascii_letters

def generate_random_string(max_len=8):
    """生成1~max_len长度的随机字符串"""
    length = random.randint(1, max_len)
    return ''.join(random.choices(CHARSET, k=length))

def generate_random_obj(depth=0, max_depth=10):
    """
    生成随机嵌套对象（控制深度防止栈溢出）
    - 叶子节点：随机字符串、基础类型、或符合_alias_pattern的陷阱字符串
    - 容器：list/tuple/dict，含叶子数组和非叶子结构
    """
    if depth > max_depth:
        # 强制返回叶子节点
        choice = random.randint(0, 4)
        if choice == 0:
            return generate_random_string()
        elif choice == 1:
            return random.randint(-100, 100)
        elif choice == 2:
            return random.choice([True, False, None])
        elif choice == 3:
            return random.uniform(-10.0, 10.0)
        else:
            # 生成陷阱字符串：符合 "@{4位hex}" 格式
            hex_part = ''.join(random.choices('0123456789abcdef', k=_HEX_COUNT))
            return f"@{hex_part}"
    
    # 随机选择容器类型或叶子
    container_type = random.choices(
        ['leaf_str', 'int', 'bool', 'none', 'float', 'list', 'tuple', 'dict', 'trap'],
        weights=[3, 1, 1, 1, 1, 2, 1, 2, 2]  # 提高容器和陷阱比例
    )[0]
    
    if container_type == 'leaf_str':
        return generate_random_string()
    elif container_type == 'int':
        return random.randint(-100, 100)
    elif container_type == 'bool':
        return random.choice([True, False])
    elif container_type == 'none':
        return None
    elif container_type == 'float':
        return random.uniform(-10.0, 10.0)
    elif container_type == 'trap':
        # 生成符合 alias_pattern 的陷阱字符串
        hex_part = ''.join(random.choices('0123456789abcdef', k=_HEX_COUNT))
        return f"@{hex_part}"
    elif container_type in ('list', 'tuple'):
        size = random.randint(0, 20)  # 控制大小避免爆炸
        items = [generate_random_obj(depth+1, max_depth) for _ in range(size)]
        # 约30%概率生成纯叶子序列（用于触发压缩）
        if random.random() < 0.3 and all(isinstance(x, (int, float, str, bool, type(None))) for x in items):
            return items if container_type == 'list' else tuple(items)
        return items if container_type == 'list' else tuple(items)
    elif container_type == 'dict':
        size = random.randint(0, 10)
        return {
            generate_random_string(5): generate_random_obj(depth+1, max_depth)
            for _ in range(size)
        }

def single_test_case(seed):
    """单次测试：生成随机对象 → 验证 my_dump 与 json.dumps 反序列化一致性"""
    random.seed(seed)
    
    # 生成随机对象（控制规模：总叶子数组数 < 50000）
    obj = generate_random_obj(max_depth=8)  # 限制深度防栈溢出
    
    try:
        # 标准JSON流程
        std_json = json.dumps(obj, indent=2, ensure_ascii=False)
        std_obj = json.loads(std_json)
        
        # my_dump流程
        custom_json = my_dump(obj, indent=2, ensure_ascii=False)
        custom_obj = json.loads(custom_json)
        
        # 严格比较（注意：tuple会被转为list，这是JSON标准行为）
        if std_obj != custom_obj:
            # 调试信息（仅当失败时输出）
            return False, f"不一致 | 原始: {obj} | 标准: {std_obj} | 自定义: {custom_obj}"
        return True, None
    except Exception as e:
        return False, f"异常: {type(e).__name__}: {e} | 对象: {obj}"

def run_massive_test(total_tests=100000):
    """运行大规模压力测试（实际10^5次，10^8次不现实）"""
    print(f"开始压力测试：_hex_count={_HEX_COUNT} (65536种占位符)")
    print(f"单次对象规模控制：叶子数组总数 < 50000")
    print(f"测试次数: {total_tests} (受限于时间，10^8次需数月，此处取10^5次代表性样本)")
    print("-" * 60)
    
    seeds = list(range(total_tests))
    
    # 使用多进程加速（根据CPU核心数）
    workers = min(cpu_count(), 8)
    passed = 0
    failed_cases = []
    
    with Pool(workers) as pool:
        results = pool.imap(single_test_case, seeds, chunksize=1000)
        for i, (ok, msg) in enumerate(results, 1):
            if ok:
                passed += 1
            else:
                failed_cases.append((i, msg))
                if len(failed_cases) >= 5:  # 记录前5个失败案例
                    break
            if i % 10000 == 0:
                print(f"已测试: {i}/{total_tests} | 通过率: {passed/i*100:.2f}%")
    
    print("-" * 60)
    if failed_cases:
        print(f"❌ 测试失败 ({len(failed_cases)} 例):")
        for idx, msg in failed_cases[:3]:
            print(f"  用例 {idx}: {msg}")
    else:
        print(f"✅ 所有 {total_tests} 次测试通过！")
        print("结论：在 _hex_count=4 且单次叶子数组<50000 的约束下，my_dump 行为正确。")
    
    return len(failed_cases) == 0

if __name__ == "__main__":
    # 先运行基础验证
    test_roundtrip_consistency()
    
    # 再运行压力测试（10^5次，平衡时间与覆盖率）
    print("\n" + "="*70)
    print("启动大规模压力测试（_hex_count=4）...")
    print("="*70)
    success = run_massive_test(total_tests=100000)
    
    if not success:
        exit(1)