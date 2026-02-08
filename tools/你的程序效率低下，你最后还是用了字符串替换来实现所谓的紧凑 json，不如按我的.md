你的程序效率低下，你最后还是用了字符串替换来实现所谓的紧凑 json，不如按我的思路实现：
```
from typing import Any, Dict, List, Optional,Tuple
import re,json

def _is_leaf_sequence(obj: Any) -> bool:
    """判断是否为叶子序列（list/tuple + 元素全为基础类型）"""
    if not isinstance(obj, (list, tuple)):
        return False
    return all(isinstance(x, (int, float, str, bool, type(None))) for x in obj)

# 载入 MD5 码模块
import hashlib
# 载入 UUID 模块
import uuid
_hex_count = 32
def my_dump(obj: Any, **kwargs) -> str:
    # 先进行一次 dumps，避免哈希冲突，而且可以进行自定义类型的处理
    json_str0 = json.dumps( obj,**kwargs )
    # 用于匹配在JSON 格式化为 "@{_hex_count个点十六进制数字}" 的字符串，并且仅提取其中的十六进制数
    _alias_pattern=r'"@([0-9a-fA-F]{' + str(_hex_count) + r'})"'
    # 检索 json_str0 符合 alias 模式的内容，提取其中的十六进制数，将其加入到 alias_set
    alias_set = set(re.findall(_alias_pattern, json_str0))
    # alias_obj_list = [(hash1,json1),... ] ，其中 hash1 是十六进制数，json1 是对应用于替换 json_str1 中 hash1 为 json1
    alias_obj_list = list()
    # 递归处理，将所有叶子节点替换为 "@{hash}"
    def replace_with_alias(obj):
        nonlocal alias_set,alias_obj_list
        if _is_leaf_sequence(obj):
            while True:
                hash_code = uuid.uuid4().hex[:_hex_count] # 取前 _hex_count 位
                if hash_code not in alias_set:
                    break       
            alias_set.add(hash_code) # 用于避免哈希重复
            alias_obj_list.append((
                '"@{}"'.format(hash_code), 
                json.dumps(obj) # 不缩进，即紧凑模式
                ))
            return "@" + hash_code # 替换为占位符
        elif isinstance(obj, dict):
            return {key:replace_with_alias(val) for key,val in obj.items()}
        else:
            return obj

    obj1 = replace_with_alias(obj) # 得到叶子list的哈希码映射表 和 被替换为哈希码的 obj
    json_str1 = json.dumps(obj1,**kwargs )

    start = 0
    json2_list = []
    for alias,leaf_json in alias_obj_list:
        # 查找 json_str 中的 '"{alias}"' 假名字符串替换为 json.dump(leaf_list)
        # 提示由于 alias 是有序的，因此可以用 .startswith() 来加速查找和替换过程（可以使平均查找时间减半）。
        index = json_str1.find(alias,start)
        json2_list.append(json_str1[start:index])
        json2_list.append(leaf_json)
        start = index + len(alias)
    json2_list.append(json_str1[start:])

    return "".join(json2_list)
```
请写出该函数以及测试代码，需要保证 my_dump 与 json.dump 的输出的 json_str 具有相同的还原性：
```
for case in 测试样例:
    json0 = json.dump(case,...)
    json1 = my_dump(case,...)
    obj0 = json.load(json0)
    obj1 = json.load(json1)
    assert obj0 is equal to obj1
```

现在我会将 _hex_count 设为 4，然后请在该代码后面进行更严格的随机测试，包括但不限于：
进行大量的以 '"{}[]@' 和 0-9,A-Z,a-z 组成的长度为 1~8 的字符串的随机测试，并且加大符合 _alias_pattern 的字符串。
由于 4 位的 hex 可以容纳 65536 种不同的值，因此被测的对象都总字符串数量最好不要超过 50000，这些字符串可以由 list、tuple、dict 等容器多层嵌套组合而成（嵌套层数至多1000层）。
采用多进程测试 10^8 次，每一次都是独立的（alias_set 重置），因此不用担心哈希冲突，只有通过此压力测试，才能保证该代码的正确性。
