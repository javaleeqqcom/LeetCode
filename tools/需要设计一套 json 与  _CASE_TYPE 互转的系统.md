附件中代码中的 CompactLeafListEncoder 设计是失败的，因为 json 会优先在父类匹配原生类型的编码，不会执行子类的 default 函数。
关键证据在于 json_test(Inheritance).py 即便用原生类型的继承，也不会触发 自定义类，
而包装类型 json_test(wrapper).py 则可以触发自定义类。
现在我需要设计一套 json <-> _CASE_TYPE 互转的系统，要求仅函基础类型的数组采用压缩json格式（不换行）。并且能够保存、读取自定义类型如 ListNode到json文件。
对于如下方案的可行性：
1. 单向序列化：
   1.1 对于叶子层数组，最好是限制数组元素除了 None 只有一种类型，包装为自定义的 array 类型，但是转换后的格式与常规数组不indent时保持一致。如此可仅以实现单向序列化，即只支持 array 转 json，但 json 读取时会误认为是普通数组。
   1.2 对于自定义类型，务必要能双向序列化。
   - 优点：json文件直观反映自定义类型；
   - 缺点：实现复杂
已经得到了初步验证（执行程序如下）：
```
(base) PS D:\Users\java_lee\Documents\GitHub\LeetCode> & C:/Users/john/anaconda3/python.exe "d:/Users/java_lee/Documents/GitHub/LeetCode/tools/json_test(directed).py"
============================================================
生成的JSON（叶子数组单行，结构保留缩进）:
============================================================
{
  "short_int": [1, 2, 3],
  "long_int": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49],
  "str_arr": ["apple", "banana", "cherry"],
  "mixed_prim": [1, "text", null, true, 3.14, false],
  "nested": {
    "inner_leaf": [10, 20, 30],
    "inner_non_leaf": [
      {
        "a": 1
      },
      {
        "b": [4, 5]
      }
    ]
  },
  "edge_cases": {
    "empty": [],
    "all_none": [null, null, null],
    "single": [42]
  },
  "non_leaf_preserved": [
    {
      "name": "item1",
      "tags": ["x", "y"]
    },
    {
    },
    },
    },
    },
    {
      "name": "item2"
    }
  ]
}
============================================================
✓ 验证1：反序列化数据与原始数据完全一致
✓ 验证2：所有叶子数组在JSON中均为单行
✓ 验证3：非叶子结构保留缩进格式
✓ 验证4：长数组（50元素）完整单行，无换行

✅ 所有测试通过！定向序列化方案验证成功
💡 核心优势：
   • 序列化：叶子数组单行（人工友好），结构保留缩进
   • 反序列化：JSON库自然解析为普通列表（零成本）
   • 无侵入：不修改原始数据，不依赖第三方库
   • 安全：UUID标记避免冲突，精确字符串替换
(base) PS D:\Users\java_lee\Documents\GitHub\LeetCode>
```
现在需要继续实现 1.2，现在有如下方案：
2. 使用 `json.dumps` 原生的自定义类转字典，和钩子函数实现（参考json_Complex_test）：
   - 优点：简单
   - 缺点：不美观
3. 使用自定义格式实现，更美观，并且与字典不可能混淆：
   - 例如 ListNode 类型转化为如下文本："<ListNode>(1,2,3,4,5,null)"
   - 优点：美观
   - 缺点：json 转回自定义格式可能无法实现，或者需要第三方库。


你的程序有可能导致哈希爆炸，即随机压力测试可能死循环。为了更科学的测试，测试通过后即可使用，我已经用类包装了（如下代码若无错误则不改动，即不用输出）：
```py
# ==================== 核心类实现 ====================
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
            hex_count: 占位符十六进制长度（默认32）
            alias_prefix: 占位符前缀（默认"@"）
        """
        if hex_len <= 0:
            raise ValueError("hex_count must be positive")
        if not alias_prefix:
            raise ValueError("alias_prefix cannot be empty")
            
        self._hex_len = hex_len
        self._max_hash_num = load_factor_threshold * (16**hex_len)
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
                    else: # 仅当出现哈希冲突时再检查负载因子，减少正常情况下的查询开销
                        assert len(alias_set) < self._max_hash_num, "The load factor has reached the threshold, and it is forbidden to insert a hash table, so please increase the hex_len size"
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
```
修改思路：
1. 用一个 depth 通过倒数来代替 depth, max_depth ，倒数为0时禁止递归，代码更简洁，符合树的思想。
2. generate_random_obj 放入 single_test_case 内作为内部函数，并维持一个 total_hash_num 记录叶子结点总数（定义在single_test_case 中，但是generate_random_obj可以读写）。
3. 简化 generate_random_obj 的逻辑：
4. 根据数学期望来预估 depth：
  - 设生成陷阱字符串的概率为p0；递归数组概率为 pl，期望长度为 nl ；递归字典概率为 pd，期望长度为 nd，另外字典键值为陷阱字符串的概率为 pk，（p0+pl+pd<1，pk<1）
  - 设深度 depth 的叶子结点数期望为 E(depth)
  - 则 E(0)=p0，depth>0时：E(depth) = p0 + (dl*nl + pd*nd)*E(depth-1) + pd*nd*pk
需要实现的代码：
```伪代码
single_test_case(){
  hex_len = 4
  生成陷阱字符串的函数(){...}

  total_hash_num = 0
  total_hash_max = 负载因子 * 16**
  E_depth = [...] # 预计算不同层数的 hash_num 数量期望值，用于动态调整 depth （可以下调不能上调）
  generate_random_obj(depth){
    if depth == 0{
      仅生成基础类型
      if 是 _alias_pattern 的字符串{
        if total_hash_num < total_hash_max{
          total_hash_num ++;
          return 该字符串
        }else{ // 超出 total_hash_max
          return None // 不再生成任何东西，直接返回 None
        }
      }
      else{...} // 其他基础类型正常生成
    }else{
      生成字典或数组，长度为随机数 sub_len
      if 为字典{
        先提前生成 keys;
        hash_num_in_keys = keys 中符合 _alias_pattern 的数量
        if hash_num_in_keys + total_hash_num > total_hash_max{
          return None; // 无法容纳该字典，返回 None
        }
        total_hash_num += hash_num_in_keys
      }else if(total_hash_num + 1 > total_hash_max){
        return None; // 连一个叶子数组都无法容纳
      }
      // 根据层数预估 total_hash_num
      for(d = 0..depth-1){
        if (total_hash_num + sub_len*E_depth[d] > total_hash_num)break;
      }
      total_hash_num ++; // 先提前占用一个 叶子数组的可能
      // 得到数学期望上的层数上限 d
      sub = 复合类型(递归 generate_random_obj(d))
      if( sub != 叶子数组){
        total_hash_num --; //不是叶子数组再退还
      }
      return sub
    }
  }
  比较结果是否正确……
}
```
修改模板：
```py
class _test_for_CompactedJson(CompactedJson): # 也可以多进程一个 python 专业测试类 utt? 忘记啥名字了
    # ==================== 严格压力测试 ====================
    CHARSET = '"' + "'" + "{}[]@" + string.digits + string.ascii_letters

    # （不可能生成陷阱字符串的字符集）
    def generate_random_string(max_len=8):
        """生成1~max_len长度的随机字符串"""
        length = random.randint(1, max_len)
        while True:
            s = ''.join(random.choices(CHARSET, k=length))
            if not re.match(...):
                return s

    def test_class_implementation(cj): # cj 就是 self
        """基础功能验证"""
        cj
        test_obj = {
            "short": [1, 2, 3],
            "long": list(range(50)),
            "trap": "@abcd",  # 4位hex陷阱
            "nested": {"inner": ["a", "b"]}
        }
        custom = cj.dump(test_obj, indent=2)
        standard = json.dumps(test_obj, indent=2)
        assert json.loads(custom) == json.loads(standard)
        assert '"short": [1, 2, 3]' in custom
        assert '"long": [0, 1, 2,' in custom and '48, 49]' in custom
        print("✅ 基础功能验证通过")

    # 继承 CompactedJson，避免反复构造
    def single_test_case(cj,args):
        """单次测试：严格控制叶子数组数量 + 防死循环保障"""
        seed, hex_len = args
        random.seed(seed)
        ……

        obj = None
        for _ in range(max_attempts):
            leaf_array_count = 0  # 重置计数器
            # 动态计算安全深度：基于几何级数期望（简化版）
            # E(d) ≈ (1 + 0.6*5 + 0.4*2*3)^d，取d使E(d) < max_leaf_arrays/2
            base_expect = 1 + 0.6 * 5 + 0.4 * 2 * 3  # ≈ 6.4
            safe_depth = max(1, min(8, int((max_leaf_arrays / 2) ** (1/3))))  # 保守估计
            obj = generate_random_obj(safe_depth)
            
        # ===== 核心验证 =====
        try:
            std_json = json.dumps(obj, indent=2, ensure_ascii=False)
            std_obj = json.loads(std_json)
            
            custom_json = cj.dump(obj, indent=2, ensure_ascii=False)
            custom_obj = json.loads(custom_json)
            
            if std_obj != custom_obj:
                return False, f"数据不一致 | 叶子数组数: {leaf_array_count}"
            return True, None
        except Exception as e:
            return False, f"异常: {type(e).__name__} | 叶子数组数: {leaf_array_count} | {str(e)[:100]}"

def run_massive_test(total_tests: int = 100000, hex_len: int = 4):
    """大规模压力测试（防死循环+资源安全）"""
    print(f"\n{'='*70}")
    print(f"🚀 启动压力测试 | hex_len={hex_len} | 容量={16**hex_len} | 安全阈值={int(0.7*(16**hex_len))}")
    print(f"📊 测试总量: {total_tests:,} | 进程数: {min(cpu_count(), 8)}")
    print(f"🛡️  防护措施: 叶子数组安全阈值=70%容量 | 深度动态调控")
    print(f"{'='*70}\n")
    
    seeds = [(i, hex_len) for i in range(total_tests)]
    workers = min(cpu_count(), 8)
    passed, failed = 0, []
    
    with Pool(workers) as pool:
        results = pool.imap(single_test_case, seeds, chunksize=2000)
        for i, (ok, msg) in enumerate(results, 1):
            if ok:
                passed += 1
            else:
                failed.append((i, msg))
                if len(failed) >= 5:
                    break
            if i % 10000 == 0 or i == total_tests:
                print(f"进度: {i:,}/{total_tests:,} | 通过率: {passed/i*100:.2f}%")
    
    print(f"\n{'='*70}")
    if failed:
        print(f"❌ 失败 {len(failed)} 例（前3例）:")
        for idx, msg in failed[:3]:
            print(f"  #{idx}: {msg}")
        return False
    else:
        print(f"✅ 全部 {total_tests:,} 次测试通过！")
        print("✅ 验证结论:")
        print(f"   • 在 hex_len={hex_len}（容量={16**hex_len}）下，安全阈值内无冲突")
        print(f"   • 反序列化结果 100% 与标准 json.dumps 一致")
        print(f"   • 无死循环（max_attempts 防护生效）")
        print(f"   • 陷阱字符串（含占位符格式）处理正确")
    print(f"{'='*70}")
    return True

if __name__ == "__main__":
    test_class_implementation()
    # 严格压力测试：hex_len=4（65536容量），测试10万次
    success = run_massive_test(total_tests=100000, hex_len=4)
    exit(0 if success else 1)
```
