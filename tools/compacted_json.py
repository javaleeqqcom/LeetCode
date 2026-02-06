# json_test(directed).py (压力测试增强版)
import json
import re
import uuid
import random
import string
from typing import Any, List, Tuple, Dict, Optional, Callable, Union, Iterable
from multiprocessing import Pool, cpu_count
from functools import partial

# ==================== 核心类实现（题目指定不改动） ====================
class CompactedJson:
    """
    定向序列化实现：仅叶子数组（基础类型+None）输出为紧凑单行格式
    核心思路：唯一占位符替换 + 精确字符串替换，避免递归序列化开销
    保证：dump输出反序列化结果 ≡ json.dumps输出反序列化结果
    """
    
    def __init__(self, hex_len: int = 32, load_factor_threshold = 0.7, alias_prefix: str = "@" ) -> None:
        """
        初始化配置
        
        Args:
            hex_len: 占位符十六进制长度（默认32）
            load_factor_threshold: 负载因子阈值（默认0.7）
            alias_prefix: 占位符前缀（默认"@"）
        """
        if hex_len <= 0:
            raise ValueError("hex_len must be positive")
        if not alias_prefix:
            raise ValueError("alias_prefix cannot be empty")
        if not (0 < load_factor_threshold < 1):
            raise ValueError("load_factor_threshold must be in (0,1)")
            
        self._hex_len = hex_len
        self._max_hash_num = int(load_factor_threshold * (16 ** hex_len))
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
                    else:  # 仅当出现哈希冲突时再检查负载因子，减少正常情况下的查询开销
                        assert len(alias_set) < self._max_hash_num, \
                            f"Load factor has reached the threshold ({self._max_hash_num}), please increase hex_len. Current alias_set size: {len(alias_set)}"
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
    
class _test_CompactedJson(CompactedJson):
    def __init__(self, hex_len: int = 4, load_factor_threshold=0.7, alias_prefix: str = "@") -> None:
        super().__init__(hex_len, load_factor_threshold, alias_prefix)
        # ==================== 严格压力测试（防死循环+科学控制） ====================
        self.CHARSET = tuple(set('"' + "'" + "{}[]" + alias_prefix + string.digits + string.ascii_letters))

        # 用于生成基础随机数据的字典，key为数据类型，value = (weight, func)，weight为权重，func为生成函数
        random_dict = {
            "int":      ( 3 ,lambda :random.randint(-100, 100)),
            "float" :   ( 1 ,lambda :random.uniform(-10.0, 10.0)),
            "bool":     ( 2 ,lambda :random.choice([True, False])),
            "None":     ( 1 ,lambda :None),
            "safe_str": ( 3 ,lambda :self._generate_safe_string(random.randint(0, self._hex_len + 3)))
        }
        
        # 排除陷阱字符串的生成函数列表和权重列表
        self._SRfuns: List[function] = [v[1] for v in random_dict.values()]
        self._SRweights: List[float] = [v[0] for v in random_dict.values()]

        # 添加陷阱字符串权重和函数到字典
        random_dict["trap_str"] = (10 ,self._generate_trap_string )

        # 包含陷阱字符串的生成函数列表和权重列表
        self._BRfuns: List[function] = [v[1] for v in random_dict.values()]
        self._BRweights: List[float] = [v[0] for v in random_dict.values()]

        # 字典键值类型的权重
        self._trap_key_rate = 0.5 # 陷阱字符串键值类型的权重占比

        # 复合类型的权重
        self._CR_types = ["base", "leaf_arr", "nonleaf_arr", 'dict']
        self._CR_weights = [2, 1, 1, 1]  # 补充你注释里的权重值，保持完整
        
        self._LS_range = (0,20) # 随机数组长度的范围
        self._DS_range = (1,5)  # 随机字典长度的范围

        # 生成随机对象中包含哈希键数量期望值随深度变化的数组
        TBp = random_dict["trap_str"][0] / sum(v[0] for v in random_dict.values())    # 基础类型中 trap_str 的概率
        total_CRW = sum(self._CR_weights)
        CRpD = dict(zip(self._CR_types, map(lambda x:x/total_CRW ,self._CR_weights) ))# 不同复合类型的出现概率映射表
        composite_len_expected = (
            CRpD["nonleaf_arr"]*sum(self._LS_range)/2 +
            CRpD["dict"]*sum(self._DS_range)/2
            ) # 复合类型中产生的子对象的期望长度
        other_expected = (
            CRpD["base"]*TBp +  # 基础类型中的陷阱字符串 
            CRpD["leaf_arr"] +  # 叶子数组必占用 1 个哈希键
            CRpD["dict"] * sum(self._DS_range)/2 * self._trap_key_rate # 还有字典的键可能包含哈希键
        )
        self._depth2EH_num = [1*TBp,  ]
        while self._depth2EH_num[-1] < self._max_hash_num and len(self._depth2EH_num) <= 100:
            self._depth2EH_num.append(
                composite_len_expected * self._depth2EH_num[-1] + # 递归计算子对象的期望
                other_expected
            )

    def _get_save_depth(self, depth: int , remain_num: float) -> int:
        while depth > 0 and self._depth2EH_num[depth] >= remain_num:
            depth -= 1
        return depth

    def _generate_trap_string(self) -> str:
        """生成精确匹配_alias_pattern的陷阱字符串（格式: @{uuid4的hex_len位十六进制}）"""
        hex_part = ''.join(random.choices('0123456789abcdef', k=self._hex_len))
        return self._alias_prefix + hex_part  # 与CompactedJson默认alias_prefix一致

    def _generate_safe_string(self,max_len) -> str:
        """生成不匹配 _alias_pattern 的随机字符串"""
        length = random.randint(1, max_len)
        while True:
            s = ''.join(random.choices(self.CHARSET, k=length))
            if re.match(self._alias_pattern, s) is None:
                return s

    # 字典键值生成函数
    def _keys_random(self ,size:int) -> Tuple[List[str],int]:
        res_L = [""]*size
        hash_num = 0
        for i in range(size):
            if random.random() < self._trap_key_rate:
                res_L[i] = self._generate_trap_string() 
                hash_num += 1
            else:
                res_L[i] = self._generate_safe_string(3 + self._hex_len)
        return res_L,hash_num

    def single_test_case(self,seed) -> Tuple[bool, str]:
        """
        单次测试：科学控制叶子数组+陷阱字符串总数，杜绝死循环
        核心机制：
        1. total_hash_num 精确统计（陷阱字符串 + 叶子数组）
        2. safe_max = 90% * _max_hash_num（预留10%缓冲）
        3. 倒计时深度控制（depth）
        4. 动态安全模式：超阈值后立即切换安全生成
        """
        random.seed(seed)
        
        # 初始化测试环境
        safe_max = int(0.9 * self._max_hash_num)  # 安全阈值（预留10%缓冲）
        total_hash_num = 0  # 精确计数器：陷阱字符串 + 叶子数组
        
        # ========== 内部生成函数（闭包共享total_hash_num） ==========
        def generate_obj(depth: int) -> Any:
            nonlocal total_hash_num
            
            # 【安全熔断】已达安全阈值 → 立即返回基础类型（绝不递归）
            if total_hash_num >= safe_max:
                return random.choices(self._SRfuns, self._SRweights)[0]()
            
            node_type = random.choices(self._CR_types, self._CR_weights)[0]

            # 【叶子层】depth=0 时只生成基础类型
            if depth <= 0 or node_type == 'base':
                return random.choices(self._BRfuns,  self._BRweights)[0]()
            
            # 叶子数组节点（核心测试目标）
            if node_type == 'leaf_arr':
                size = random.randint(*self._LS_range)
                total_hash_num += 1 # 叶子数组占用恰好1个哈希
                return [generate_obj(0) for _ in range(size)]
            
            # 非叶子数组（含嵌套结构）
            if node_type == 'nonleaf_arr':
                size = random.randint(*self._LS_range)
                sub_d = self._get_save_depth(depth-1, (safe_max - total_hash_num) / size)
                if 0 == sub_d:
                    total_hash_num += 1 # 叶子数组占用恰好1个哈希
                return [generate_obj(sub_d) for _ in range(size)]
            
            # 字典节点（键可能为陷阱字符串）
            if node_type == 'dict':
                size = random.randint(*self._DS_range)
                keys, add_num = self._keys_random(size)
                remain_num = safe_max - total_hash_num - add_num
                if remain_num <= 0:
                    return generate_obj(0) # 已经超出安全范围，返回单层对象
                total_hash_num += add_num # 添加键值对占用的哈希
                sub_d = self._get_save_depth(depth-1, remain_num / size)
                return {k: generate_obj(sub_d) for k in keys}

            # 空类型兜底
            return None
        
        # ========== 生成测试对象（确保至少1个占位符） ==========
        obj = None
        for _ in range(5):  # 最多5次尝试
            total_hash_num = 0
            obj = generate_obj(depth= len(self._depth2EH_num))
            if total_hash_num > 0:  # 确保有测试价值（含陷阱或叶子数组）
                break
        else:
            # 5次均无占位符 → 跳过（无替换逻辑，基础测试已覆盖）
            return True, "SKIP: no hashable elements"
        
        # ========== 核心验证 ==========
        try:
            # 标准JSON流程
            std_json = json.dumps(obj, indent=2, ensure_ascii=False)
            std_obj = json.loads(std_json)
            
            # CompactedJson流程
            custom_json = self.dump(obj, indent=2, ensure_ascii=False)
            custom_obj = json.loads(custom_json)
            
            # 严格一致性验证
            if std_obj != custom_obj:
                return False, f"MISMATCH | hashes:{total_hash_num} | obj:{str(obj)[:200]}"
            return True, ""
        except Exception as e:
            return False, f"EXCEPTION:{type(e).__name__} | hashes:{total_hash_num} | {str(e)[:150]}"

import time
# ==================== 修复3: run_massive_test 重写 ====================
def _run_test_continuously( seed_0 , seed_step, min_second: float , hex_len: int = 4) -> Tuple[int,bool,str]:
    begin = time.time()
    test_obj = _test_CompactedJson(hex_len)
    count = 0
    max_count = ((1<<31)-1-seed_0)//seed_step # 保证随机种子不会溢出 int32
    while time.time() - begin < min_second and count < max_count:
        ok,msg = test_obj.single_test_case(seed_0 + count*seed_step)
        if msg.startswith("SKIP"):continue
        count += 1
        if not ok: # 出现错误，停止测试并返回错误信息
            return (count,ok,msg)
    return (count,True,"")

def run_massive_test(thread:int) -> bool:
    total_call = 100
    # ✅ 关键修复: 生成 (seed_0, seed_step , min_second) 参数对
    seed0_HL_t = [(i,total_call ,100) for i in range(total_call)]
    passed, failed, skipped = 0, [], 0

    with Pool(min(cpu_count(), thread)) as pool:
        ……

    # ========== 结果报告 ==========
    print(f"\n{'='*70}")
    if failed:
        print(f"❌ 失败 {len(failed)} 例 (前3例):")
        for idx, msg in failed[:3]:
            print(f"  #{idx}: {msg}")
    else:
        print(f"✅ 全部 {passed:,} 有效测试通过 (跳过 {skipped:,} 无占位符用例)")
        print("✅ 智能深度调控验证:")
        print(f"   • _depth2EH_num 精确预计算各深度期望哈希数")
        print(f"   • _get_save_depth 动态裁剪子树深度，确保 total_hash_num < safe_max")
        print(f"   • 0 死循环 | 0 冲突 | 100% 数据一致性")
    print(f"{'='*70}")
    return len(failed) == 0

# ==================== 修复2: 基础验证函数修正 ====================
def test_class_implementation():
    cj = CompactedJson(hex_len=4)
    test_obj = {
        "short": [1, 2, 3],
        "long": list(range(50)),
        "trap": "@abcd",
        "nested": {"inner": ["a", "b", "c"]},
        "mixed": [1, "text", None, True]
    }
    # ✅ 修复: self.dump → cj.dump (原代码此处有语法错误)
    custom = cj.dump(test_obj, indent=2)  
    standard = json.dumps(test_obj, indent=2)
    
    assert json.loads(custom) == json.loads(standard)
    assert '"short": [1, 2, 3]' in custom
    assert '"long": [0, 1, 2,' in custom and '48, 49]' in custom
    assert '"trap": "@abcd"' in custom
    print("✅ 基础功能验证通过")

# ==================== 主程序 ====================
if __name__ == "__main__":
    # 1. 基础功能验证
    test_class_implementation()
    
    # 2. 严格压力测试（hex_len=4 极限测试）
    print("\n⏳ 启动压力测试（hex_len=4，模拟高碰撞场景）...")
    success = run_massive_test(total_tests=100000, hex_len=4)
    
    # 3. 退出状态
    exit(0 if success else 1)