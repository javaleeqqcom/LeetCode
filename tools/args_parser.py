from __future__ import annotations  # 必须放在文件第一行
from typing import Any, Dict, Tuple, Callable ,Union,List ,Optional,Deque,TypedDict,NotRequired,Generic,TypeVar,Iterator
# try:
#     from tools.args_parser_tools import _is_base_type,_extract_actual_type,_formated_string,ReprDecorator # 此部分代表过于冗长故放在 args_parser_tools
#     from tools.iter_node_tools import ListNodeKitBase,TreeNodeKitBase
# except:
from args_parser_tools import _is_base_type,_extract_actual_type,_formated_string,ReprDecorator # 此部分代表过于冗长故放在 args_parser_tools
from iter_node_tools import ListNodeKitBase,TreeNodeKitBase

from collections import deque
import inspect
import math,os,random # leetcode 平台会自动嵌入一些常用库，学生无需导入也能执行

type _BASE_TYPE = Union[
    int,float,bool,None,str, 
    List["_BASE_TYPE"], 
    Dict[Union[str, int], "_BASE_TYPE"]
]

_ARGS = Tuple[_BASE_TYPE,...]
_KWARGS = Dict[str,_BASE_TYPE]
# <request>题目标准输入类型 _INPUT_PARAMS，要么是 args 元组，要么是 kwargs 字典，且都只能由基础类型组成
_PARAMS = Union[_ARGS,_KWARGS]

class _CASE(TypedDict):
    input: _PARAMS
    cid: Union[int,str]
    expected: NotRequired[_BASE_TYPE]
    output: NotRequired[_BASE_TYPE]

# 待改进，采用泛型而非 Union
_EXECUTE_CALLER = Union[
    Callable[[Any ,_PARAMS] , _BASE_TYPE],
    Callable[[Any,_KWARGS],_BASE_TYPE],
    Callable[[Any,_ARGS],_BASE_TYPE]
]

# 示例：LeetCode 常见结构（学生可按题追加）
class ListNode:
    def __init__(self, val:_BASE_TYPE=0, next:Optional[ListNode]=None):
        self.val = val
        self.next = next

# ====== 转换函数 ======
def List2ListNode(lst: List[_BASE_TYPE]) -> Optional[ListNode]:
    head = ListNode(lst[0])
    cur = head
    for val in lst[1:]:
        cur.next = ListNode(val)
        cur = cur.next
    return head

class ListNodeKit(ListNodeKitBase): #[ListNode]):
    """链表调试增强工具，提供安全的扁平化、环检测和打印功能。

    该类基于 ListNodeKitBase 和 ListNodeKitDecorator 实现，
    将原生 ListNode 节点包装为增强对象，保持链式操作的类型一致性。

    主要特性:
        - 空链表判断: 通过 `if link:` 判断是否非空，不支持 `if link is not None`。
        - 索引访问: `link[i]` 返回第 i 个节点的包装对象；长度为 n 的无环链表 link，索引范围为 [0,n]，其中 link[n] 返回空链表，索引越界时抛出 IndexError。
        - 扁平化与环检测: `nodes, cycle_idx = link.flatten()` 返回节点列表和环起始索引(无环为 None)。
        - 字符串表示: `str(link)` 输出带环标记的格式，例如 `[1,2,3,4,5]` 或 `[1,2,3,>4,5^]`(> 表示环起点，^ 表示环尾)。
        - 类型保持: `link.next` 返回的是 ListNodeKit 实例，而非原始节点或 None，便于连续访问。
        - 提取原生节点：`link.node` 返回原生节点 ListNode 对象。

    示例:
    （待添加实例）
    注意:
        - 空链表 (`ListNodeKit(None)`) 无法使用 `next` 属性，访问会抛出 AttributeError。
        - 若链表存在环，索引 n 会迭代 n 次，请优先使用 flatten 检测环。
    """
    @classmethod
    def from_val(cls, val: _BASE_TYPE) -> 'ListNodeKit':
        """创建单节点树，并设置节点值为 val"""
        return cls(ListNode(val))
    
    def to_str(self, max_len=-1):
        return self._to_string(self, "val", max_len)

    def __repr__(self):
        return self._to_string(self, "val")
    
    
# 若方法需要返回一个 ListNode，则必须实现 ListNode2List ，以便测试结果的对比。注意该方法进行无环才运行执行
def ListNode2List(node: Optional[ListNode]) -> List[_BASE_TYPE]:
    nodes,circle = ListNodeKit(node).flatten()
    assert circle != -1, "参数 ListNode 代表的链表有环！"
    return [node.val for node in nodes]

# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val:_BASE_TYPE=0, left:Optional[TreeNode]=None, right:Optional[TreeNode]=None):
        self.val = val
        self.left = left
        self.right = right

# 在 args_parser.py 中添加 TreeNodeKit 类（继承自 TreeNodeKitBase）
class TreeNodeKit(TreeNodeKitBase): #[TreeNode]):
    """
    二叉树调试增强工具，提供安全的层序遍历、环检测和索引访问。
    用法与 ListNodeKit 类似，支持从原始节点或从层序列表构造。
    """
    @classmethod
    def from_level_order(cls, level_order: List[_BASE_TYPE]) -> 'TreeNodeKit':
        """TreeNodeKit.from_level_order(level_order=[1,2,3]) : 从层序列表构建树"""
        from .args_parser import List2TreeNode
        root = List2TreeNode(level_order)
        return cls(root)

    @classmethod
    def from_val(cls, val: _BASE_TYPE) -> 'TreeNodeKit':
        """创建单节点树，并设置节点值为 val"""
        return cls(TreeNode(val))
    
    def to_str(self, max_depth=10, max_node_len=-1, full_traversal=False):
        return self._to_string(self, "val", max_depth, max_node_len, full_traversal)

    def __repr__(self):
        return self._to_string(self, "val")
    
def TreeNode2List(root: Optional[TreeNode]) -> List[_BASE_TYPE]:
    """将 TreeNode 转换为完全二叉树层序列表（含 None 占位）"""
    if not root:
        return []
    
    result = []
    q:Deque[Optional[TreeNode]] = deque([root])
    while q:
        node = q.popleft()
        if node is None:
            result.append(None)
        else:
            result.append(node.val)
            q.append(node.left)
            q.append(node.right)
    
    # 去除尾部多余的 None（保持与输入格式一致）
    while result and result[-1] is None:
        result.pop()
    
    return result

def List2TreeNode(level_order: List[_BASE_TYPE]) -> Optional[TreeNode]:
    if not level_order or level_order[0] is None:
        return None
    root = TreeNode(level_order[0])
    q = deque([root])
    i = 1
    while q and i < len(level_order):
        node = q.popleft()
        if i < len(level_order) and level_order[i] is not None:
            node.left = TreeNode(level_order[i])
            q.append(node.left)
        i += 1
        if i < len(level_order) and level_order[i] is not None:
            node.right = TreeNode(level_order[i])
            q.append(node.right)
        i += 1
    return root

# ====== 【核心】注册转换规则 ======
# 注册表：键 = (目标类型, 源类型)，值 = 转换函数
input_parser_registry: Dict[Tuple[type, type], Callable ] = {
    (list, ListNode): List2ListNode,
    (list, TreeNode): List2TreeNode,
    # 可按需求扩展
    # python 的 list 自动对应 JSON 的数组，
}

output_parser_registry: Dict[type,Callable] = {
    ListNode : ListNode2List,
    TreeNode : TreeNode2List
}

def _exchange_DIY_types(the_fun:Callable,sig_type:type,value:Any,error_prefix:str)->List[Any]:
    sig_type = _extract_actual_type(sig_type)
    if sig_type == value.__class__:
        return value
    else:
        try:
            return input_parser_registry[(value.__class__, sig_type)](value)
        except KeyError:
            raise ValueError(f"{error_prefix} 的输入类型 {value.__class__} 无法转化为函数 {the_fun.__name__} 所需的类型 {sig_type}。")
        except Exception as e:
            raise ValueError(f"{error_prefix} 的输入类型 {value.__class__} 无法转化为函数 {the_fun.__name__} 所需的类型 {sig_type}，错误信息：\n{e}")

def parse_output_to_standard(obj: Any, depth: int = 0) -> Any:
    """
    将对象转换为 JSON 可序列化的类型
    利用 output_parser_registry 一次性智能转换自定义类型
    """
    # 超过 3 层，停止检查，避免如采用嵌套数组表示二叉树的情况
    # 如果是 list[DIY 类型]，一般 DIY 类型不会太深
    if depth > 3:
        return obj
    
    # 检查是否是 output_parser_registry 中注册的自定义类型
    obj_type = type(obj)
    if obj_type in output_parser_registry:
        return output_parser_registry[obj_type](obj)
    
    # 处理字典 - 递归转换所有值
    if isinstance(obj, dict):
        return {
            key: parse_output_to_standard(value, depth + 1)
            for key, value in obj.items()
        }
    
    # 处理列表 - 递归转换所有元素
    if isinstance(obj, list):
        # 如果列表为空或第一个元素是 JSON 原生类型，不需要深度检查后续元素
        if not obj or isinstance(obj[0], (str, int, float, bool, type(None))):
            return obj
        # 否则递归转换每个元素
        return [parse_output_to_standard(item, depth + 1) for item in obj]
    
    # 处理元组返回
    if isinstance(obj, tuple):
        return tuple(parse_output_to_standard(item, depth + 1) for item in obj)
    
    # JSON 原生支持的类型直接返回
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    
    # 其他类型，尝试转为字符串，方便追查错误
    return str(obj)

# 如下基础类型由 json.dump json.load 自动完成双向转化，无需额外注册转换方法：
# 1. 题目中的数组，在 python 中一律以 list 格式为准（输入不会出现 tuple）。
# 2. 题目中的 true 和 false 对应 python 的 True 和 False。
# 3. 题目中的 null ，对应 python 的 None，特别地题目在数组中以 null 作为空指针占位，只需要在 python 代码的 list 构造 None 占位即可。
# 另外：python 的 tuple 不会出现在函数输入输出中，所有数组都以 python list 形式出现。

def _i_pname2ErrorMsg(i_pname:Union[int,str])->str:
    if isinstance(i_pname,int): return f"第 {i_pname} 个题目参数"
    else: return f"题目参数 {i_pname}"
    
def parse_standard_input(value:_BASE_TYPE,sig_type:inspect.Parameter,func_name:str,i_pname:Union[int,str]) -> Any:
    act_type = _extract_actual_type(sig_type.annotation)
    if act_type == value.__class__:
        return value
    else:
        try:
            return input_parser_registry[(value.__class__, act_type)](value)
        except KeyError:
            raise ValueError(f"{_i_pname2ErrorMsg(i_pname)}的类型 {value.__class__} 无法转化为主函数 {func_name} 所需的类型 {sig_type}。")
        except Exception as e:
            raise ValueError(f"主函数 {func_name} 在转化{_i_pname2ErrorMsg(i_pname)}时出现意外，错误信息：\n{e}")
