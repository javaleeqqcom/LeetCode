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