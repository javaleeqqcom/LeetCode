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

