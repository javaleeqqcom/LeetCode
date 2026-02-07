# json_test(directed).py (压力测试增强版)
import json
import re
import uuid
import random
import string
from typing import Any, List, Tuple, Dict, Optional, Callable, Union, Iterable
from multiprocessing import Pool, cpu_count
from functools import partial
import numpy as np

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
        
        # 包含复合类型，一次性进行随机投掷
        self._type_weights_dict = {
            # 安全类型
            "int":     3,
            "float" : 1,
            "bool":  2,
            "None":  1,
            "safe_str": 3,
            # 陷阱类型
            "trap_str": 10,
            # 复合类型
            "leaf_arr": 10,
            "nonleaf_arr":10,
            'dict':10,
        }

        self._base_funs = (
            lambda :random.randint(-100, 100),
            lambda :random.uniform(-10.0, 10.0),
            lambda :random.choice([True, False]),
            lambda :None,
            self._generate_safe_string,
            self._generate_trap_string,
        )

        self._types = tuple(self._type_weights_dict.keys())
        self._weights = np.array([w for w in self._type_weights_dict.values()],dtype=np.float32)
        self._weights /= self._weights.sum()

        self._base_weights = self._weights[:len(self._base_funs)]
        self._base_weights /= self._base_weights.sum()

        # 字典键值类型的权重
        self._trap_key_rate = 0.5 # 陷阱字符串键值类型的权重占比
 
        self._LLS_range = (0,50) # 叶子数组长度的范围
        self._NLS_range = (1,20) # 随机非叶子数组长度的范围
        self._DS_range = (1,5)  # 随机字典长度的范围

        # 生成随机对象中包含哈希键数量期望值随深度变化的数组
        # 复合类型中产生的子对象的期望长度 = 复合类型概率 与 子对象的期望长度 的内积
        composite_len_expected = (
            self._weights[self._types.index("nonleaf_arr")]*sum(self._NLS_range)/2 +
            self._weights[self._types.index("dict")]*sum(self._DS_range)/2
            )
        # 其他类型的期望长度
        other_expected = (
            self._weights[self._types.index("trap_str")] +  # 基础类型中的陷阱字符串 
            self._weights[self._types.index("leaf_arr")] +  # 叶子数组必占用 1 个哈希键
            self._weights[self._types.index("dict")]*sum(self._DS_range)/2 * self._trap_key_rate # 还有字典的键可能包含哈希键
        )
        # 第 0 层，只能从基础随机对象中生成，其中只有 traps_str 可能包含 1 个哈希键
        self._depth2EH_num = [self._base_weights[self._types.index("trap_str")],  ]
        while self._depth2EH_num[-1] < self._max_hash_num and len(self._depth2EH_num) <= 100:
            self._depth2EH_num.append(
                composite_len_expected * self._depth2EH_num[-1] + other_expected # 迭代求解子对象的期望
            )

    def _get_save_depth(self, depth: int , remain: int , sub_size:int) -> int:
        if sub_size<=0: return 0
        flat = remain/sub_size
        while depth > 0 and self._depth2EH_num[depth] >= flat:
            depth -= 1
        return depth

    def _generate_trap_string(self) -> str:
        """生成精确匹配_alias_pattern的陷阱字符串（格式: @{uuid4的hex_len位十六进制}）"""
        hex_part = ''.join(random.choices('0123456789abcdef', k=self._hex_len))
        return self._alias_prefix + hex_part  # 与CompactedJson默认alias_prefix一致

    def _generate_safe_string(self) -> str:
        """生成不匹配 _alias_pattern 的随机字符串"""
        length = random.randint(1, self._hex_len+3)
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
                res_L[i] = self._generate_safe_string()
        return res_L,hash_num

    # 注： depth 是子元素的层级上限，因此此处不 - 1
    def generate_list(self,depth: int, remain:int, size:int) -> Tuple[List[Any],int]:
        assert remain>0
        remain -= 1 # 因为 res 有可能占用 哈希数，先预减1
        depth = self._get_save_depth(depth,remain,size) # 重新预估深度
        res = []
        for _ in range(size):
            if remain >0:
                sub ,remain = self.generate_obj(depth,remain)
                res.append(sub)
            else:break
        # 若返回的不是叶子序列，哈希数 还原+1
        if depth>0 and (not self._is_leaf_sequence(res)):
            return res,remain +1
        else:
            return res,remain

    # ========== 递归生成函数（禁用全局变量） ==========
    def generate_obj(self,depth: int, remain:int) -> Tuple[Any,int]:
        # 【安全熔断】已达安全阈值 → 禁用 trap_str
        if remain <= 0:
            type_index = random.choices(range(len(self._base_funs)-1), self._base_weights[:-1])[0]
        # 【叶子层】depth=0 时只生成基础类型
        elif depth <= 0:
            type_index = random.choices(range(len(self._base_funs)), self._base_weights)[0]
        else:
            type_index = random.choices(range(len(self._weights)), self._weights.tolist())[0]

        if type_index < len(self._base_funs): # 是基础类型，直接返回函数和占用的哈希
            return self._base_funs[type_index](), int(self._types[type_index] == "trap_str") # 特别注意！陷阱字符串占用 1 个哈希
        elif self._types[type_index] == 'leaf_arr': # 叶子数组节点（核心测试目标）
            return self.generate_list(0,remain,random.randint(*self._LLS_range))
        elif self._types[type_index] == 'nonleaf_arr':# 非叶子数组（含嵌套结构）
            return self.generate_list(depth-1,remain,random.randint(*self._NLS_range))
        elif self._types[type_index] == 'dict': # 字典节点（键可能为陷阱字符串）
            size = random.randint(*self._DS_range)
            # 先分配键，避免递归浪费
            keys, hash_num = self._keys_random(size)
            if remain <= hash_num: return {},remain # 无法分配足够的哈希，返回空字典
            # 再生成值（如果哈希数量紧缺，自然会降低消耗哈希的数量）
            values,remain = self.generate_list(depth-1,remain - hash_num,size)
            return dict(zip(keys,values)),remain

        # 空类型兜底
        return None,remain
    
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
        
        # ========== 生成测试对象（确保至少1个占位符） ==========
        obj = None
        for _ in range(5):  # 最多5次尝试
            obj,remain = self.generate_obj(len(self._depth2EH_num),safe_max)
            if safe_max > remain:  # 确保有测试价值（含陷阱或叶子数组）
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
                return False, f"MISMATCH | hashes:{safe_max - remain} | obj:{str(obj)[:200]}"
            return True, ""
        except Exception as e:
            return False, f"EXCEPTION:{type(e).__name__} | hashes:{safe_max - remain} | {str(e)[:150]}"
        

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

import time
from multiprocessing import Pool, cpu_count
from typing import Tuple, Optional, Union, List

def _run_test_continuously(args: Tuple[int, int, float, int]) -> Tuple[int, int, str, int, int]:
    """
    单进程持续测试：复用单个测试实例，按时间窗口循环
    返回: (有效测试数, 通过数, 失败信息, 跳过数, hex_len)
    """
    seed_0, seed_step, min_second, hex_len = args
    tester = _test_CompactedJson(hex_len=hex_len)  # ✅ 每进程仅初始化1次
    start = time.time()
    valid_cnt = pass_cnt = skip_cnt = 0
    max_iter = ((1 << 31) - 1 - seed_0) // seed_step  # 防seed溢出
    
    iter_idx = 0
    while (time.time() - start < min_second) and (iter_idx < max_iter):
        seed = seed_0 + iter_idx * seed_step
        ok, msg = tester.single_test_case(seed)
        
        if msg.startswith("SKIP"):
            skip_cnt += 1
        else:
            valid_cnt += 1
            if ok:
                pass_cnt += 1
            else:
                # ✅ 遇失败立即返回（保留失败现场 + 当前hex_len）
                return (valid_cnt, pass_cnt, msg, skip_cnt, hex_len)
        iter_idx += 1
    
    return (valid_cnt, pass_cnt, "", skip_cnt, hex_len)  # 全部通过

def run_massive_test(
    thread: Optional[int] = None, 
    hex_len: Union[int, List[int]] = 2, 
    duration_sec: float = 100.0
) -> bool:
    """
    智能压力测试：多hex_len并发验证 + 精确进度反馈
    参数:
        thread: 每个hex_len分配的进程数 (None=自动)
        hex_len: 单个或多个hex_len值
        duration_sec: 每进程最小运行时间(秒)
    """
    thread = min(cpu_count(), 8) if thread is None else thread
    hex_len_list = [hex_len] if isinstance(hex_len, int) else hex_len
    pool_cnt = thread * len(hex_len_list)
    per_second = duration_sec/len(hex_len_list)
    
    # ========== 动态生成测试概览 ==========
    print(f"\n{'='*70}")
    print(f"🚀 多参数压力测试 | hex_len={hex_len_list} | 总进程数: {pool_cnt} ({thread}×{len(hex_len_list)})")
    for hl in hex_len_list:
        max_cap = 16 ** hl
        safe_thresh = int(0.7 * max_cap * 0.9)  # 理论安全阈值 (load_factor=0.7, 安全系数0.9)
        print(f"   • hex_len={hl}: 容量={max_cap:,} | 理论安全阈值≈{safe_thresh:,}")
    print(f"⏱️  每进程运行 ≥{per_second:.1f}s | 总测试时长 ≈{duration_sec:.1f}s (并发)")
    print(f"💡 优化核心: 每进程复用单实例 | seed分配: 进程i → seeds = [i, i+{pool_cnt}, ...]")
    print(f"   • 遇首个失败立即熔断 | 收集≥5失败则全局终止")
    print(f"{'='*70}\n")
    
    # ✅ 任务分配: (seed_0, seed_step=总进程数, 运行时长, hex_len)
    # 每个hex_len分配连续thread个进程，确保负载均衡
    tasks = [
        (i, pool_cnt, per_second, hex_len_list[i // thread])
        for i in range(pool_cnt)
    ]
    
    total_pass = total_skip = 0
    failures = []  # 存储 (任务ID, hex_len, 失败信息)
    start_global = time.time()
    
    with Pool(thread) as pool:
        # imap_unordered: 任一进程失败立即反馈（加速故障发现）
        for task_idx, result in enumerate(
            pool.imap_unordered(_run_test_continuously, tasks, chunksize=1), 1
        ):
            valid, passed, fail_msg, skipped, current_hex_len = result
            total_pass += passed
            total_skip += skipped
            
            if fail_msg:
                failures.append((task_idx, current_hex_len, fail_msg))
                if len(failures) >= 5:
                    pool.terminate()
                    pool.join()
                    break
            
            # 精确进度反馈（含当前hex_len和实时速率）
            elapsed = time.time() - start_global
            rate = total_pass / elapsed if elapsed > 0.1 else 0
            status = "⚠️" if fail_msg else "✅"
            print(f"{status} 任务{task_idx}/{pool_cnt} (hex_len={current_hex_len}) | "
                  f"本任务: 有效{valid}(失败{valid - passed}, 跳过{skipped}) | "
                  f"累计通过{total_pass} | 总速率{rate:.1f} tests/s")
    
    # ========== 结果报告 ==========
    total_time = time.time() - start_global
    total_valid = total_pass + len(failures)  # 有效测试总数（含失败用例）
    
    print(f"\n{'='*70}")
    print(f"⏱️  总耗时: {total_time:.1f}s | 平均速率: {total_pass/total_time:.1f} 有效测试/秒")
    print(f"📊 总计: 有效测试 {total_valid:,} | 通过 {total_pass:,} | 跳过 {total_skip:,} | 失败 {len(failures)}")
    
    if failures:
        print(f"\n❌ 失败 {len(failures)} 例 (前3例):")
        for task_id, hl, msg in failures[:3]:
            # 从失败信息中提取关键阈值（如"threshold (179)"）
            print(f"  [任务#{task_id} | hex_len={hl}] {msg}")
        print(f"\n💡 根本原因分析:")
        print(f"   • 失败信息中 'threshold (X)' 即当前hex_len的_max_hash_num")
        print(f"   • 检查 _depth2EH_num 预估值是否显著低于实际生成量")
        print(f"   • 重点验证: 字典键trap_str贡献 + 深度0初始化 + 递归系数")
    else:
        print(f"\n✅ 全部 {total_pass:,} 个有效测试通过！(跳过 {total_skip:,} 例)")
        print("✅ 多参数验证成功:")
        print(f"   • 所有 hex_len ∈ {hex_len_list} 均通过压力测试")
        print(f"   • _get_save_depth 动态裁剪确保 total_hash_num < 安全阈值")
        print(f"   • 0 死循环 | 0 哈希冲突 | 100% 数据一致性")
        print(f"   • 资源优化: 初始化开销降低 {pool_cnt} 倍（{pool_cnt}任务 × 1实例/任务）")
    
    print(f"{'='*70}")
    return len(failures) == 0

# ==================== 主程序 ====================
if __name__ == "__main__":
    # 1. 基础功能验证
    test_class_implementation()
    
    # 2. 打印关键配置（验证修复效果）
    test_obj = _test_CompactedJson(hex_len=2)
    print("\n🔧 预估模型关键参数 (hex_len=2):")
    print(f"   • _type_weights_dict: {dict(list(test_obj._type_weights_dict.items())[:3])}... (共{len(test_obj._type_weights_dict)}项)")
    print(f"   • _trap_key_rate: {test_obj._trap_key_rate}")
    print(f"   • _depth2EH_num[:3]: {[round(x, 4) for x in test_obj._depth2EH_num[:3]]}")
    print(f"   • 理论安全阈值: {int(0.7 * (16**2) * 0.9)} | _max_hash_num: {test_obj._max_hash_num}\n")
    
    # 3. 多参数压力测试（覆盖边界场景）
    success = run_massive_test(
        thread=12, 
        hex_len=[2, 3, 4 ,5],
        duration_sec=600.0    # 每进程60秒（总测试时长约60秒）
    )
    
    # 4. 退出状态
    exit(0 if success else 1)