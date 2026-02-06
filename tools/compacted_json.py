import json
import re
import uuid
from typing import Any, List, Tuple

# ==================== 核心类实现 ====================
class CompactedJson:
    """
    定向序列化实现：仅叶子数组（基础类型+None）输出为紧凑单行格式
    核心思路：唯一占位符替换 + 精确字符串替换，避免递归序列化开销
    保证：dump输出反序列化结果 ≡ json.dumps输出反序列化结果
    """
    
    def __init__(self, hex_len: int = 32, alias_prefix: str = "@") -> None:
        """
        初始化配置
        
        Args:
            hex_count: 占位符十六进制长度（默认32）
            alias_prefix: 占位符前缀（默认"@"）
        """
        if hex_len <= 0:
            raise ValueError("hex_count must be positive")
        if not alias_prefix:
            raise ValueError("alias_prefix cannot be empty")
            
        self._hex_len = hex_len
        self._max_hash_num = 一个合理的哈希容量比例（适合再哈希法，一旦超过该比例，应考虑扩容） * (16**hex_len)
        self._alias_prefix = alias_prefix
        # 动态构建正则表达式（转义特殊字符）
        escaped_prefix = re.escape(alias_prefix)
        self._alias_pattern = re.compile(rf'"({escaped_prefix}[0-9a-fA-F]{{{hex_len}}})"')

    def _is_leaf_sequence(self, obj: Any) -> bool:
        """判断是否为叶子序列（list/tuple + 元素全为基础类型）"""
        if not isinstance(obj, (list, tuple)):
            return False
        return all(isinstance(x, (int, float, str, bool, type(None))) for x in obj)

    def dump(self, obj: Any, **kwargs) -> str:
        """
        定向序列化：外层结构保留缩进，叶子数组强制单行紧凑输出
        保证反序列化结果与标准 json.dumps 完全一致
        
        Args:
            obj: 要序列化的对象
            **kwargs: 传递给 json.dumps 的参数（如 indent, ensure_ascii 等）
            
        Returns:
            str: 序列化后的JSON字符串
        """
        # 步骤1: 提取原始数据中已存在的占位符（避免冲突）
        json_str0 = json.dumps(obj, **kwargs)
        alias_set = set(self._alias_pattern.findall(json_str0))
        
        # 步骤2: 递归替换叶子序列为唯一占位符，构建映射表
        alias_obj_list: List[Tuple[str, str]] = []  # [(占位符JSON字符串, 紧凑数组JSON字符串), ...]
        
        def replace_with_alias(sub_obj: Any) -> Any:
            if self._is_leaf_sequence(sub_obj):
                # 生成唯一占位符（避开原始数据中已存在的）
                while True:
                    hash_code = uuid.uuid4().hex[:self._hex_len]
                    placeholder = self._alias_prefix + hash_code
                    if placeholder not in alias_set:
                        break
                    else:
                        assert len(alias_set) < self._max_hash_num, 哈希数超过了限制，无法继续生成新的占位符
                alias_set.add(placeholder)
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
        
        # 步骤4: 按顺序精准替换
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

# ==================== 使用示例与验证 ====================
def test_class_implementation():
    """验证类实现的正确性"""
    # 测试默认配置
    cj_default = CompactedJson()
    test_obj = {
        "short": [1, 2, 3],
        "long": list(range(50)),
        "nested": {"inner": [10, 20, 30]},
        "trap": "@abcd1234"  # 包含陷阱字符串
    }
    
    result1 = cj_default.dump(test_obj, indent=2)
    std_result = json.dumps(test_obj, indent=2)
    
    # 验证反序列化一致性
    assert json.loads(result1) == json.loads(std_result)
    
    # 验证叶子数组单行
    assert '"short": [1, 2, 3]' in result1
    assert '"long": [0, 1, 2,' in result1 and '48, 49]' in result1
    
    # 测试自定义配置 (_hex_count=4, alias_prefix="#")
    cj_custom = CompactedJson(hex_len=4, alias_prefix="#")
    test_obj2 = {"data": ["a", "b", "c"], "trap": "#12ab"}
    result2 = cj_custom.dump(test_obj2, indent=2)
    assert json.loads(result2) == json.loads(json.dumps(test_obj2, indent=2))
    
    print("✅ 类实现验证通过！")

# -------------------- 随机压力测试 --------------------------------
import random
import string
from multiprocessing import Pool, cpu_count

# 字符集：包含 '"{}[]@' 和 0-9,A-Z,a-z
CHARSET = '"' + "'" + "{}[]@" + string.digits + string.ascii_letters

def generate_random_string(max_len=8):
    """生成1~max_len长度的随机字符串"""
    length = random.randint(1, max_len)
    return ''.join(random.choices(CHARSET, k=length))

def generate_random_obj(depth=0, max_depth=8, hex_count=4):
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
            # 生成陷阱字符串：符合 "@{hex_count位hex}" 格式
            hex_part = ''.join(random.choices('0123456789abcdef', k=hex_count))
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
        hex_part = ''.join(random.choices('0123456789abcdef', k=hex_count))
        return f"@{hex_part}"
    elif container_type in ('list', 'tuple'):
        size = random.randint(0, 20)  # 控制大小避免爆炸
        items = [generate_random_obj(depth+1, max_depth, hex_count) for _ in range(size)]
        # 约30%概率生成纯叶子序列（用于触发压缩）
        if random.random() < 0.3 and all(isinstance(x, (int, float, str, bool, type(None))) for x in items):
            return items if container_type == 'list' else tuple(items)
        return items if container_type == 'list' else tuple(items)
    elif container_type == 'dict':
        size = random.randint(0, 10)
        return {
            generate_random_string(5): generate_random_obj(depth+1, max_depth, hex_count)
            for _ in range(size)
        }

def single_test_case(args):
    """单次测试：生成随机对象 → 验证 dump 与 json.dumps 反序列化一致性"""
    seed, hex_count = args
    random.seed(seed)
    
    # 创建测试实例
    cj = CompactedJson(hex_len=hex_count)
    
    # 生成随机对象（控制规模：总叶子数组数 < 50000）
    obj = generate_random_obj(max_depth=8, hex_count=hex_count)
    
    try:
        # 标准JSON流程
        std_json = json.dumps(obj, indent=2, ensure_ascii=False)
        std_obj = json.loads(std_json)
        
        # my_dump流程
        custom_json = cj.dump(obj, indent=2, ensure_ascii=False)
        custom_obj = json.loads(custom_json)
        
        # 严格比较（注意：tuple会被转为list，这是JSON标准行为）
        if std_obj != custom_obj:
            return False, f"不一致 | 原始: {obj} | 标准: {std_obj} | 自定义: {custom_obj}"
        return True, None
    except Exception as e:
        return False, f"异常: {type(e).__name__}: {e} | 对象: {obj}"

def run_massive_test(total_tests=100000, hex_count=4 ,thread = 8):
    """运行大规模压力测试"""
    print(f"开始压力测试：hex_count={hex_count} ({16**hex_count}种占位符)")
    print(f"单次对象规模控制：叶子数组总数 < 50000")
    print(f"测试次数: {total_tests}")
    print("-" * 60)
    
    # 准备参数：每个测试用例需要 (seed, hex_count)
    test_args = [(i, hex_count) for i in range(total_tests)]
    
    # 使用多进程加速
    workers = min(cpu_count(), thread)
    passed = 0
    failed_cases = []
    
    with Pool(workers) as pool:
        # 修正：使用 starmap 处理多参数，或保持 imap 但传入元组
        results = pool.imap(single_test_case, test_args, chunksize=1000)
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
        print(f"结论：在 hex_count={hex_count} 且单次叶子数组<50000 的约束下，dump 行为正确。")
    
    return len(failed_cases) == 0

if __name__ == "__main__":
    # 先运行基础验证
    test_class_implementation()
    
    # 再运行压力测试（使用4位hex进行高强度测试）
    print("\n" + "="*70)
    print("启动大规模压力测试（hex_count=4）...")
    print("="*70)
    success = run_massive_test(total_tests=100000, hex_count=4)
    
    if not success:
        exit(1)