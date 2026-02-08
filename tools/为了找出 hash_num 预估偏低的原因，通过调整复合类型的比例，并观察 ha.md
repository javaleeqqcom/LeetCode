为了找出 hash_num 预估偏低的原因，通过调整复合类型的比例，并观察 hash_num 的变化趋势。
修改后的主函数：
```
# ==================== 主程序 ====================
if __name__ == "__main__":
    # 1. 基础功能验证
    test_class_implementation()
    
    test_obj = _test_CompactedJson()
    print(test_obj._CR_types)
    print(test_obj._CR_weights)
    print(test_obj._depth2EH_num[:3])
    # 2. 严格压力测试（hex_len=4 极限测试）
    success = run_massive_test(thread=12, hex_len=2)
    
    # 3. 退出状态
    exit(0 if success else 1)
```
下面是不同修改参数情况的执行结果：
1. 原始
```
(base) PS D:\Users\java_lee\Documents\GitHub\LeetCode> & C:/Users/john/anaconda3/python.exe d:/Users/java_lee/Documents/GitHub/LeetCode/tools/compacted_json.py
✅ 基础功能验证通过
['base', 'leaf_arr', 'nonleaf_arr', 'dict']
[2, 1, 1, 1]
[0.5, 2.0500000000000003, 6.235000000000001]

======================================================================
🚀 智能压力测试 | hex_len=2 | 容量=256 | 安全阈值=161
⏱️  每进程运行 ≥100.0s | 进程数: 12
💡 优化核心: 每进程复用单实例 (_test_CompactedJson初始化开销↓12倍)
   • seed分配: 进程i → seeds = [i, i+12, i+2*12, ...]
   • 遇首个失败即终止该进程 | 收集≥5失败则全局终止
======================================================================

✅ 进程1/12完成 | 本进程: 有效1(通过0) | 跳过0 | 累计有效通过0 | 速率0.0 tests/s
✅ 进程2/12完成 | 本进程: 有效8(通过7) | 跳过0 | 累计有效通过7 | 速率61.6 tests/s
✅ 进程3/12完成 | 本进程: 有效10(通过9) | 跳过0 | 累计有效通过16 | 速率138.3 tests/s
✅ 进程4/12完成 | 本进程: 有效3(通过2) | 跳过0 | 累计有效通过18 | 速率155.5 tests/s

======================================================================
⏱️  总耗时: 0.1s | 平均速率: 147.3 有效测试/秒

❌ 失败 5 例 (前3例):
  [进程#1] EXCEPTION:AssertionError | hashes:42 | Load factor has reached the threshold (179), please increase hex_len. Current alias_set size: 179
  [进程#2] EXCEPTION:AssertionError | hashes:69 | Load factor has reached the threshold (179), please increase hex_len. Current alias_set size: 195
  [进程#3] EXCEPTION:AssertionError | hashes:54 | Load factor has reached the threshold (179), please increase hex_len. Current alias_set size: 179

💡 关键洞察: 失败用例的 total_hash_num 可能逼近 161，验证 _get_save_depth 深度裁剪逻辑是否触发
======================================================================
```
2. 无 dict：
```
(base) PS D:\Users\java_lee\Documents\GitHub\LeetCode> & C:/Users/john/anaconda3/python.exe d:/Users/java_lee/Documents/GitHub/LeetCode/tools/compacted_json.py
✅ 基础功能验证通过
['base', 'leaf_arr', 'nonleaf_arr', 'dict']
[2, 1, 1, 0]
[0.5, 1.8125, 5.2578125]

======================================================================
🚀 智能压力测试 | hex_len=2 | 容量=256 | 安全阈值=161
⏱️  每进程运行 ≥100.0s | 进程数: 12
💡 优化核心: 每进程复用单实例 (_test_CompactedJson初始化开销↓12倍)
   • seed分配: 进程i → seeds = [i, i+12, i+2*12, ...]
   • 遇首个失败即终止该进程 | 收集≥5失败则全局终止
======================================================================

✅ 进程1/12完成 | 本进程: 有效2(通过1) | 跳过0 | 累计有效通过1 | 速率9.1 tests/s
✅ 进程2/12完成 | 本进程: 有效5(通过4) | 跳过0 | 累计有效通过5 | 速率43.5 tests/s
✅ 进程3/12完成 | 本进程: 有效7(通过6) | 跳过0 | 累计有效通过11 | 速率92.5 tests/s
✅ 进程4/12完成 | 本进程: 有效4(通过3) | 跳过0 | 累计有效通过14 | 速率117.7 tests/s

======================================================================
⏱️  总耗时: 0.1s | 平均速率: 119.6 有效测试/秒

❌ 失败 5 例 (前3例):
  [进程#1] EXCEPTION:AssertionError | hashes:20 | Load factor has reached the threshold (179), please increase hex_len. Current alias_set size: 179
  [进程#2] EXCEPTION:AssertionError | hashes:41 | Load factor has reached the threshold (179), please increase hex_len. Current alias_set size: 206
  [进程#3] EXCEPTION:AssertionError | hashes:34 | Load factor has reached the threshold (179), please increase hex_len. Current alias_set size: 180

💡 关键洞察: 失败用例的 total_hash_num 可能逼近 161，验证 _get_save_depth 深度裁剪逻辑是否触发
======================================================================
```
3. 无 nonleaf_arr：
```
(base) PS D:\Users\java_lee\Documents\GitHub\LeetCode> & C:/Users/john/anaconda3/python.exe d:/Users/java_lee/Documents/GitHub/LeetCode/tools/compacted_json.py
✅ 基础功能验证通过
['base', 'leaf_arr', 'nonleaf_arr', 'dict']
[2, 1, 0, 1]
[0.5, 1.25, 1.8125]

======================================================================
🚀 智能压力测试 | hex_len=2 | 容量=256 | 安全阈值=161
⏱️  每进程运行 ≥100.0s | 进程数: 12
💡 优化核心: 每进程复用单实例 (_test_CompactedJson初始化开销↓12倍)
   • seed分配: 进程i → seeds = [i, i+12, i+2*12, ...]
   • 遇首个失败即终止该进程 | 收集≥5失败则全局终止
======================================================================

✅ 进程1/12完成 | 本进程: 有效43(通过42) | 跳过1 | 累计有效通过42 | 速率338.5 tests/s
✅ 进程2/12完成 | 本进程: 有效34(通过33) | 跳过0 | 累计有效通过75 | 速率599.7 tests/s
✅ 进程3/12完成 | 本进程: 有效19(通过18) | 跳过0 | 累计有效通过93 | 速率691.1 tests/s
✅ 进程4/12完成 | 本进程: 有效10(通过9) | 跳过0 | 累计有效通过102 | 速率749.6 tests/s

======================================================================
⏱️  总耗时: 0.1s | 平均速率: 1186.5 有效测试/秒

❌ 失败 5 例 (前3例):
  [进程#1] EXCEPTION:AssertionError | hashes:60 | Load factor has reached the threshold (179), please increase hex_len. Current alias_set size: 179
  [进程#2] EXCEPTION:AssertionError | hashes:63 | Load factor has reached the threshold (179), please increase hex_len. Current alias_set size: 188
  [进程#3] EXCEPTION:AssertionError | hashes:83 | Load factor has reached the threshold (179), please increase hex_len. Current alias_set size: 199

💡 关键洞察: 失败用例的 total_hash_num 可能逼近 161，验证 _get_save_depth 深度裁剪逻辑是否触发
======================================================================
```
4. 不主动生成 leaf_arr （但可能间接生成）
```
(base) PS D:\Users\java_lee\Documents\GitHub\LeetCode> & C:/Users/john/anaconda3/python.exe d:/Users/java_lee/Documents/GitHub/LeetCode/tools/compacted_json.py
✅ 基础功能验证通过
['base', 'leaf_arr', 'nonleaf_arr', 'dict']
[2, 0, 1, 1]
[0.5, 2.3125, 8.4296875]

======================================================================
🚀 智能压力测试 | hex_len=2 | 容量=256 | 安全阈值=161
⏱️  每进程运行 ≥100.0s | 进程数: 12
💡 优化核心: 每进程复用单实例 (_test_CompactedJson初始化开销↓12倍)
   • seed分配: 进程i → seeds = [i, i+12, i+2*12, ...]
   • 遇首个失败即终止该进程 | 收集≥5失败则全局终止
======================================================================

✅ 进程1/12完成 | 本进程: 有效14(通过13) | 跳过0 | 累计有效通过13 | 速率84.0 tests/s
✅ 进程2/12完成 | 本进程: 有效3(通过2) | 跳过0 | 累计有效通过15 | 速率96.3 tests/s
✅ 进程3/12完成 | 本进程: 有效12(通过11) | 跳过1 | 累计有效通过26 | 速率155.4 tests/s
✅ 进程4/12完成 | 本进程: 有效38(通过37) | 跳过0 | 累计有效通过63 | 速率358.4 tests/s

======================================================================
⏱️  总耗时: 0.2s | 平均速率: 520.8 有效测试/秒

❌ 失败 5 例 (前3例):
  [进程#1] EXCEPTION:AssertionError | hashes:76 | Load factor has reached the threshold (179), please increase hex_len. Current alias_set size: 182
  [进程#2] EXCEPTION:AssertionError | hashes:69 | Load factor has reached the threshold (179), please increase hex_len. Current alias_set size: 180
  [进程#3] EXCEPTION:AssertionError | hashes:103 | Load factor has reached the threshold (179), please increase hex_len. Current alias_set size: 187

💡 关键洞察: 失败用例的 total_hash_num 可能逼近 161，验证 _get_save_depth 深度裁剪逻辑是否触发
======================================================================
```
5. 无 trap_str（可观察 self._depth2EH_num 体现）：
```
        # 添加陷阱字符串权重和函数到字典
        random_dict["trap_str"] = (0 ,self._generate_trap_string )

        # 包含陷阱字符串的生成函数列表和权重列表
        self._BRfuns: List[function] = [v[1] for v in random_dict.values()]
        self._BRweights: List[float] = [v[0] for v in random_dict.values()]

        # 字典键值类型的权重
        self._trap_key_rate = 0.0 # 陷阱字符串键值类型的权重占比
(base) PS D:\Users\java_lee\Documents\GitHub\LeetCode> & C:/Users/john/anaconda3/python.exe d:/Users/java_lee/Documents/GitHub/LeetCode/tools/compacted_json.py
✅ 基础功能验证通过
['base', 'leaf_arr', 'nonleaf_arr', 'dict']
[2, 1, 1, 1]
[0.0, 0.2, 0.74]

======================================================================
🚀 智能压力测试 | hex_len=2 | 容量=256 | 安全阈值=161
⏱️  每进程运行 ≥100.0s | 进程数: 12
💡 优化核心: 每进程复用单实例 (_test_CompactedJson初始化开销↓12倍)
   • seed分配: 进程i → seeds = [i, i+12, i+2*12, ...]
   • 遇首个失败即终止该进程 | 收集≥5失败则全局终止
======================================================================

✅ 进程1/12完成 | 本进程: 有效10759(通过10759) | 跳过167 | 累计有效通过10759 | 速率107.5 tests/s
✅ 进程2/12完成 | 本进程: 有效10666(通过10666) | 跳过165 | 累计有效通过21425 | 速率214.0 tests/s
✅ 进程3/12完成 | 本进程: 有效10258(通过10258) | 跳过153 | 累计有效通过31683 | 速率316.4 tests/s
✅ 进程4/12完成 | 本进程: 有效10533(通过10533) | 跳过158 | 累计有效通过42216 | 速率421.6 tests/s
✅ 进程5/12完成 | 本进程: 有效10475(通过10475) | 跳过175 | 累计有效通过52691 | 速率526.2 tests/s
✅ 进程6/12完成 | 本进程: 有效10740(通过10740) | 跳过159 | 累计有效通过63431 | 速率633.4 tests/s
✅ 进程7/12完成 | 本进程: 有效10529(通过10529) | 跳过133 | 累计有效通过73960 | 速率738.6 tests/s
✅ 进程8/12完成 | 本进程: 有效10734(通过10734) | 跳过176 | 累计有效通过84694 | 速率845.7 tests/s
✅ 进程9/12完成 | 本进程: 有效10558(通过10558) | 跳过164 | 累计有效通过95252 | 速率951.1 tests/s
✅ 进程10/12完成 | 本进程: 有效10400(通过10400) | 跳过128 | 累计有效通过105652 | 速率1054.9 tests/s
✅ 进程11/12完成 | 本进程: 有效10516(通过10516) | 跳过138 | 累计有效通过116168 | 速率1159.9 tests/s
✅ 进程12/12完成 | 本进程: 有效10313(通过10313) | 跳过138 | 累计有效通过126481 | 速率1262.8 tests/s

======================================================================
⏱️  总耗时: 100.2s | 平均速率: 1262.7 有效测试/秒

✅ 全部 126,481 个有效测试通过！(跳过 1,854 例)
✅ 智能深度调控验证:
   • _depth2EH_num 精确预计算各深度期望哈希数
   • _get_save_depth 动态裁剪子树深度，确保 total_hash_num < safe_max
   • 0 死循环 | 0 冲突 | 100% 数据一致性
   • 资源优化: 初始化开销降低 12 倍（12进程 × 1实例/进程）
======================================================================
```