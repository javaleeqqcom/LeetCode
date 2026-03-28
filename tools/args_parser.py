from __future__ import annotations  # 必须放在文件第一行
from typing import Any, Dict, Tuple, Callable ,Union,List ,Optional,Deque,TypedDict,NotRequired,Generic,TypeVar,Iterator
try:
    from tools.args_parser_tools import _is_standard_type,_extract_actual_type,_formated_string,IterNext,SafeFlatten,ListNodeKitBase,ListNodeKitDecorator # 此部分代表过于冗长故放在 args_parser_tools
except:
    from args_parser_tools import _is_standard_type,_extract_actual_type,_formated_string,IterNext,SafeFlatten,ListNodeKitBase,ListNodeKitDecorator # 此部分代表过于冗长故放在 args_parser_tools
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

@ListNodeKitDecorator(prep_property="val")
class ListNodeKit(ListNodeKitBase):
    """链表安全调试工具，提供链表结构的增强操作，支持环检测和安全扁平化。
    
    用法:
    - 创建链表工具: link = ListNodeKit(head_node)  # head_node 应为 ListNode 或 None（空链表用 None）
      注意：谨慎使用 ListNodeKit(None) 表示空链表，它会创建一个内部 head 为 None 的对象，但不能用 link is None 进行判断，应使用 bool(link) 判定空链表为 False。
    - 索引访问: link[index] 返回链表第 index 个节点（索引从0开始，设链表长度为n）：
        * index=0 总是有效（返回链表头，即使链表为空）
        * index 在 [1, n-1] 时返回有效节点（n为链表长度）
        * index = n 时返回 ListNodeKit(None)（空节点包装）
        * index < 0 或 index > n 时抛出 IndexError
        * 若链表有环时，索引访问不会检查环
    - 环检测: nodes, cycle_idx = link.flatten()
        输入: 无
        输出: (list, int) - 节点列表和环起始索引（-1 表示无环）
    - 安全打印: link.to_string() 返回链表字符串表示
        输入: 无
        输出: str - 格式如 [1,2,3,4,5] 或 [1,2,3,4,5,>^]（> 表示环起点，^ 表示结尾）

    关键注意事项:
    1. 空链表表示: 应使用 None (head = None) 而非 ListNodeKit(None)
       - 正确: head = None
       - 错误: link = ListNodeKit(None)  # 会创建对象，但不是空链表表示
    2. 空链表检查: 由于重载了 __bool__，可用 `if link:` 判断是否为空链表
       - 示例: if link: ...  # 非空链表
    3. 索引访问安全:
       - 链表为空时，link[0] 返回 link 本身（不是 None，但可用 bool()判断是否为空链表）
       - 链表非空时，索引超出范围会抛出 IndexError，避免死循环
       - 示例: 
         link = ListNodeKit(ListNode(1, None))  # 链表 [1]
         link[0]  # 返回 ListNodeKit(1) 有效
         link[1]  # 抛出 IndexError
    4. 节点访问安全: ListNodeKit(ListNode(1, None)).next 会返回 None
       - 不影响 while node: node = node.next 的循环
    5. 不修改原始链表: 所有操作不会修改原始链表结构
    6. 适用于 LeetCode 链表问题测试验证
    """
    pass

# 若方法需要返回一个 ListNode，则必须实现 ListNode2List ，以便测试结果的对比。注意该方法进行无环才运行执行
def ListNode2List(node: Optional[ListNode]) -> List[_BASE_TYPE]:
    nodes,circle = ListNodeKit(node).flatten()
    assert circle != -1, "参数 ListNode 代表的链表有环！"
    return [node.val for node in nodes]

# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val:_BASE_TYPE=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        # 用于 log / repr：返回完全二叉树层序列表表示（含 null）
        lst = TreeNode2List(self)
        return f"<TreeNode>: {lst}"

    def print(self) -> str:
        """返回美观的树形字符串（仅限前几层，适合人类阅读）"""
        if not self:
            return "<empty tree>"
        
        # 第一步：按层收集节点（保留 None 占位，但叶子层之后不再扩展）
        levels = []
        q:Deque[Optional[TreeNode]] = deque([self])
        max_levels = 5  # 最多打印5层以防过长
        
        while q and len(levels) < max_levels:
            level_size = len(q)
            current_level = []
            has_non_null = False
            
            for _ in range(level_size):
                node = q.popleft()
                current_level.append(node)
                if node is not None:
                    q.append(node.left)
                    q.append(node.right)
                    if node.left or node.right:
                        has_non_null = True
                else:
                    q.append(None)
                    q.append(None)
            
            levels.append(current_level)
            # 如果本层全是 None 或已到最大层数，则停止
            if not has_non_null or len(levels) >= max_levels:
                break
        
        # 第二步：从最后一层开始向上构建字符串（自底向上对齐）
        # 先将每层转为字符串
        str_levels = []
        for level in levels:
            str_level = []
            for node in level:
                if node is None:
                    str_level.append("null")
                else:
                    str_level.append(str(node.val))
            str_levels.append(str_level)
        
        # 第三步：计算每层所需宽度并居中对齐
        # 从最底层开始，确定每个节点占据的宽度
        spacing = 4  # 叶子节点间的最小间隔
        lines = []
        n = len(str_levels)
        # 最底层宽度决定整体布局
        bottom_widths = [len(s) for s in str_levels[-1]]
        # 每个位置的起始坐标（字符列）
        pos = [(sum(bottom_widths[:i]) + i * spacing) for i in range(len(bottom_widths))]
        
        # 自底向上生成每一行
        for i in reversed(range(n)):
            level_strs = str_levels[i]
            # 当前层节点数
            num_nodes = len(level_strs)
            # 计算当前层每个节点在底层对应的中心位置
            centers = []
            step = len(pos) // num_nodes if num_nodes > 0 else 1
            for j in range(num_nodes):
                start_idx = j * step
                end_idx = (j + 1) * step
                if start_idx < len(pos):
                    center_pos = (pos[start_idx] + (pos[end_idx - 1] if end_idx <= len(pos) else pos[-1])) // 2
                    centers.append(center_pos)
                else:
                    centers.append(0)
            
            # 构建当前行字符串
            line_len = max(centers) + max(len(s) for s in level_strs) if centers else 0
            line = [' '] * (line_len + 1)
            for j, s in enumerate(level_strs):
                if j < len(centers):
                    start = centers[j]
                    for k, char in enumerate(s):
                        if start + k < len(line):
                            line[start + k] = char
            lines.append(''.join(line).rstrip())
        
        # 反转回从根到叶的顺序
        return '\n'.join(reversed(lines))
    
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
