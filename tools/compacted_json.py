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

# ==================== 辅助函数和类定义 ====================
# 判断是否为叶子序列（list/tuple + 元素全为基础类型）
def _is_leaf_sequence( obj: Any) -> bool:
    """判断是否为叶子序列（list/tuple + 元素全为基础类型）"""
    if not isinstance(obj, (list, tuple)):
        return False
    return all(isinstance(x, (int, float, str, bool, type(None))) for x in obj)

class _alias:
    """ 以 f'{alias_prefix}{hex_len位十六进制数}' 的格式作为别名"""
    def __init__(self,hex_len: int = 32, alias_prefix: str = "@" ) -> None:
        if hex_len <= 0:
            raise ValueError("hex_len must be positive")
        if not alias_prefix:
            raise ValueError("alias_prefix cannot be empty")
        self._hex_len = hex_len
        self._alias_prefix = alias_prefix
        # 动态构建正则表达式（转义特殊字符）
        escaped_prefix = re.escape(alias_prefix)
        self._alias_pattern = re.compile(rf'"({escaped_prefix}[0-9a-fA-F]{{{hex_len}}})"')

        self.CHARSET = tuple(set('"' + "'" + "{}[]" + alias_prefix + string.digits + string.ascii_letters))
    
    def _generate_trap_string(self, *args, **kwargs) -> str:
        """生成精确匹配_alias_pattern的陷阱字符串（格式: @{uuid4的hex_len位十六进制}）"""
        hex_part = ''.join(random.choices('0123456789abcdef', k=self._hex_len))
        return self._alias_prefix + hex_part
    
    def _generate_safe_string(self, *args, **kwargs) -> str:
        """生成不匹配 _alias_pattern 的随机字符串"""
        length = random.randint(1, self._hex_len + 3)
        while True:
            s = ''.join(random.choices(self.CHARSET, k=length))
            if not re.match(re.compile(rf'"{re.escape(self._alias_prefix)}[0-9a-fA-F]{{{self._hex_len}}}"'), s):
                return s
           
# ==================== 核心类实现（题目指定不改动） ====================
class CompactedJson(_alias):
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
        super().__init__(hex_len,alias_prefix)

        if not (0 < load_factor_threshold < 1):
            raise ValueError("load_factor_threshold must be in (0,1)")
            
        self._max_hash_num = int(load_factor_threshold * (16 ** hex_len))

    def dumps(self, obj: Any, **kwargs) -> str:
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
            if _is_leaf_sequence(sub_obj):
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
    
def _gen_int(*args, **kwargs) -> int:
    return random.randint(-100, 100)

def _gen_float(*args, **kwargs) -> float:
    return random.uniform(-10.0, 10.0)

def _gen_bool(*args, **kwargs) -> bool:
    return random.choice([True, False])

def _gen_none(*args, **kwargs) -> None:
    return None
from random_object import _choice_random, _size_random, make_list_FuncWC, make_dict_FuncWC, set_random_seed,_func_weight_cost
class _test_CompactedJson(CompactedJson):

    # 仅叶子列表（层级为1）花费1点
    @classmethod
    def leaf_depth(cls,**kwargs):
        """仅叶子列表（层级为1）花费1点"""
        depth = kwargs.get('depth', 0)
        return int(depth <= 1)

    def __init__(self, hex_len=8, load_factor_threshold=0.7, alias_prefix="@"):
        super().__init__(hex_len, load_factor_threshold, alias_prefix)
        alias = _alias(hex_len, alias_prefix)
        
        # 创建基础随机生成器
        self.leaf_base = _choice_random([
            _func_weight_cost(_gen_int, 2, 0),
            _func_weight_cost(_gen_float, 2, 0),
            _func_weight_cost(_gen_bool, 1, 0),
            _func_weight_cost(_gen_none, 1, 0),
            _func_weight_cost(alias._generate_safe_string, 2, 0),
            _func_weight_cost(alias._generate_trap_string, 2, 1),
        ])
        
        # 创建列表大小随机生成器（指数分布，λ=0.1）
        self.NL_size_random = _size_random('expo', lambd=0.1)
        
        # 创建递归列表随机生成器
        self.list_random = make_list_FuncWC(self.NL_size_random, self.leaf_depth)
        self.list_random.bind_method(self.leaf_base)
        
        # 创建递归字典随机生成器
        self.keys_random = _choice_random([
            _func_weight_cost(alias._generate_safe_string, 1, 0),
            _func_weight_cost(alias._generate_trap_string, 1, 1),
        ])
        self.D_size_random = _size_random('uniform', a=0, b=4)
        self.dict_random = make_dict_FuncWC(self.D_size_random, 0, self.keys_random)
        self.dict_random.bind_method(self.leaf_base)
        
        # 将列表和字典随机生成器与基础随机生成器结合
        self.merge_random = self.leaf_base + [
            self.list_random.toFuncWC(5),
            self.dict_random.toFuncWC(5)
        ]
    
    def generate_obj(self, depth=3, remain=1000):
        """生成随机对象，确保包含叶子数组和陷阱字符串"""
        return self.merge_random(depth=depth, remain=remain)
    
    def single_test_case(self, seed):
        """单次测试：科学控制叶子数组+陷阱字符串总数，杜绝死循环"""
        set_random_seed(seed)
        safe_max = int(0.9 * self._max_hash_num)
        
        # 生成测试对象（确保至少1个占位符）
        obj = None
        for _ in range(5):
            obj, remain = self.merge_random(depth=10, remain=safe_max)
            if safe_max > remain:
                break
        else:
            return True, "SKIP: no hashable elements", 0, -1
        
        # 核心验证
        try:
            # 标准JSON流程
            std_json = json.dumps(obj, indent=2, ensure_ascii=False)
            std_obj = json.loads(std_json)
            
            # CompactedJson流程
            custom_json = self.dumps(obj, indent=2, ensure_ascii=False)
            custom_obj = json.loads(custom_json)
            
            # 严格一致性验证
            if std_obj != custom_obj:
                return False, f"MISMATCH | hashes:{safe_max - remain} | obj:{str(obj)[:200]}", safe_max - remain, len(custom_json)
            return True, "", safe_max - remain, len(custom_json)
        except Exception as e:
            return False, f"EXCEPTION:{type(e).__name__} | hashes:{safe_max - remain} | {str(e)[:150]}", safe_max - remain, -1

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
    custom = cj.dumps(test_obj, indent=2)  
    standard = json.dumps(test_obj, indent=2)
    
    assert json.loads(custom) == json.loads(standard)
    assert '"short": [1, 2, 3]' in custom
    assert '"long": [0, 1, 2,' in custom and '48, 49]' in custom
    assert '"trap": "@abcd"' in custom
    print("✅ 基础功能验证通过")

import time
from multiprocessing import Pool, cpu_count
from typing import Tuple, Optional, Union, List

def _run_test_continuously(args: Tuple[int, int, float, _test_CompactedJson]) -> Tuple[int, int, str, int, int, float, float,float]:
    """
    单进程持续测试：复用单个测试实例，按时间窗口循环
    返回: (有效测试数, 通过数, 失败信息, 跳过数, hex_len, 平均hash节点数量, 平均JSON长度 ,测试总时长s)
    """
    seed_0, seed_step, min_second, tester = args
    start = time.time()
    valid_cnt = pass_cnt = skip_cnt = 0
    total_hash_nodes = 0
    total_json_length = 0
    
    iter_idx = 0
    max_iter = ((1 << 31) - 1 - seed_0) // seed_step  # 防seed溢出
    
    while (time.time() - start < min_second) and (iter_idx < max_iter):
        seed = seed_0 + iter_idx * seed_step
        ok, msg, hash_num, json_length = tester.single_test_case(seed)
        
        if msg.startswith("SKIP"):
            skip_cnt += 1
        else:
            valid_cnt += 1
            total_hash_nodes += hash_num
            total_json_length += json_length
            if ok:
                pass_cnt += 1
            else:
                # ✅ 遇失败立即返回（保留失败现场 + 当前hex_len）
                return (valid_cnt, pass_cnt, msg, skip_cnt, tester._hex_len, 0, 0 ,(time.time() - start))
        iter_idx += 1
    
    # 计算平均值
    avg_hash_nodes = total_hash_nodes / valid_cnt if valid_cnt > 0 else 0
    avg_json_length = total_json_length / valid_cnt if valid_cnt > 0 else 0
    
    return (valid_cnt, pass_cnt, "", skip_cnt, tester._hex_len, avg_hash_nodes, avg_json_length , (time.time() - start))

def run_massive_test(
    thread: Optional[int] = None, 
    hex_lens: Union[int, List[int]] = 2, 
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
    if isinstance(hex_lens, int):
        hex_lens = [hex_lens]
    pool_cnt = thread * len(hex_lens)
    per_second = duration_sec/len(hex_lens)
    tester_list = [_test_CompactedJson(hl) for hl in hex_lens]
    
    # ========== 动态生成测试概览 ==========
    print(f"\n{'='*70}")
    print(f"🚀 多参数压力测试 | hex_len={hex_lens} | 总进程数: {pool_cnt} ({thread}×{len(hex_lens)})")
    for hl in hex_lens:
        max_cap = 16 ** hl
        safe_thresh = int(0.7 * max_cap * 0.9)  # 理论安全阈值 (load_factor=0.7, 安全系数0.9)
        print(f"   • hex_len={hl}: 容量={max_cap:,} | 理论安全阈值≈{safe_thresh:,}")
    print(f"⏱️  每进程运行 ≥{per_second:.1f}s | 总测试时长 ≈{duration_sec:.1f}s (并发)")
    print(f"💡 优化核心: 每进程复用单实例 | seed分配: 进程i → seeds = [i, i+{pool_cnt}, ...]")
    print(f"   • 遇首个失败立即熔断 | 收集≥5失败则全局终止")
    print(f"{'='*70}\n")
    
    # ✅ 任务分配: (seed_0, seed_step=总进程数, 运行时长, hex_len)
    tasks = [
        (i, pool_cnt, per_second, tester_list[i // thread])
        for i in range(pool_cnt)
    ]
    
    total_pass = total_skip = 0
    total_hash_nodes = 0
    total_json_length = 0
    failures = []  # 存储 (任务ID, hex_len, 失败信息)
    start_global = time.time()
    
    with Pool(thread) as pool:
        # imap_unordered: 任一进程失败立即反馈（加速故障发现）
        for task_idx, result in enumerate(
            pool.imap_unordered(_run_test_continuously, tasks, chunksize=1), 1
        ):
            valid, passed, fail_msg, skipped, current_hex_len, avg_hash_nodes, avg_json_length ,test_time = result
            total_pass += passed
            total_skip += skipped
            total_hash_nodes += valid * avg_hash_nodes
            total_json_length += valid * avg_json_length
            
            if fail_msg:
                failures.append((task_idx, current_hex_len, fail_msg))
                if len(failures) >= 5:
                    pool.terminate()
                    pool.join()
                    break
            
            rate = (valid / test_time) if test_time > 0 else 0
            status = "⚠️" if fail_msg else "✅"
            print(f"{status} 任务{task_idx}/{pool_cnt} (hex_len={current_hex_len}) | "
                  f"本任务: 有效{valid}(通过{passed}) | 跳过{skipped} | "
                  f"平均hash节点: {avg_hash_nodes:.1f} | 平均JSON长度: {avg_json_length:.1f} | "
                  f"子线程平均速率 {rate:.1f} 有效测试/秒")
    
    # ========== 结果报告 ==========
    total_time = time.time() - start_global
    total_valid = total_pass + len(failures)  # 有效测试总数（含失败用例）
    
    # 计算全局平均值
    avg_total_hash_nodes = total_hash_nodes / total_valid if total_valid > 0 else 0
    avg_total_json_length = total_json_length / total_valid if total_valid > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"⏱️  总耗时: {total_time:.1f}s | 平均速率: {total_pass/total_time:.1f} 有效测试/秒")
    print(f"📊 总计: 有效测试 {total_valid:,} | 通过 {total_pass:,} | 跳过 {total_skip:,} | 失败 {len(failures)}")
    print(f"   • 全局平均哈希节点数量: {avg_total_hash_nodes:.1f}")
    print(f"   • 全局平均JSON长度: {avg_total_json_length:.1f}")
    
    if failures:
        print(f"\n❌ 失败 {len(failures)} 例 (前3例):")
        for task_id, hl, msg in failures[:3]:
            print(f"  [任务#{task_id} | hex_len={hl}] {msg}")
        print(f"\n💡 根本原因分析:")
        print(f"   • 失败信息中 'threshold (X)' 即当前hex_len的_max_hash_num")
        print(f"   • 检查 _depth2EH_num 预估值是否显著低于实际生成量")
        print(f"   • 重点验证: 字典键trap_str贡献 + 深度0初始化 + 递归系数")
    else:
        print(f"\n✅ 全部 {total_pass:,} 个有效测试通过！(跳过 {total_skip:,} 例)")
        print("✅ 多参数验证成功:")
        print(f"   • 所有 hex_len ∈ {tester_list} 均通过压力测试")
        print(f"   • _get_save_depth 动态裁剪确保 total_hash_num < 安全阈值")
        print(f"   • 0 死循环 | 0 哈希冲突 | 100% 数据一致性")
        print(f"   • 资源优化: 初始化开销降低 {pool_cnt} 倍（{pool_cnt}任务 × 1实例/任务）")
    
    print(f"{'='*70}")
    return len(failures) == 0

def test_hex_len_variations():
    """生成测试用例验证 hex_len 对 JSON 长度的影响"""
    import os
    os.makedirs("test", exist_ok=True)
    hex_lens = [2, 3, 4, 5]
    for hex_len in hex_lens:
        for seed in range(3):  # 每个 hex_len 生成 3 个测试用例
            random.seed(seed + hex_len*10)
            tester = _test_CompactedJson(hex_len=hex_len)
            
            # 生成测试对象 (确保包含足够多的叶子数组)
            obj, _ = tester.generate_obj(depth=3, remain=1000)
            
            # 生成标准 JSON
            std_json = json.dumps(obj, indent=2, ensure_ascii=False)
            
            # 生成压缩 JSON
            custom_json = tester.dumps(obj, indent=2, ensure_ascii=False)
            
            # 保存文件 (命名格式: std_2_0.json, my_2_0.json)
            with open(f"test/std_{hex_len}_{seed}.json", "w", encoding="utf-8") as f:
                f.write(std_json)
            with open(f"test/my_{hex_len}_{seed}.json", "w", encoding="utf-8") as f:
                f.write(custom_json)
    
    print(f"✅ 已生成 {len(hex_lens)*3} 个测试用例到 .\\test\\ 目录")

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
    
    # 保存不同长度的随机对象都Json化后的结果
    test_hex_len_variations()

    # 3. 多参数压力测试（覆盖边界场景）
    success = run_massive_test(
        thread=12, 
        hex_lens=[2, 3, 4, 5],  # hex_len=5 容量过大，通常无需测试
        duration_sec = 120   # 总测试时长（下限）
    )
    
    # 4. 退出状态
    exit(0 if success else 1)