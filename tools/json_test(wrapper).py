import json

# 关键修改：不再继承 list！
class LeafList:
    """自定义列表类：不继承任何序列化类型，使 JSON 库认为它是不可序列化的"""
    def __init__(self, lst):
        self.lst = lst

class CompactLeafListEncoder(json.JSONEncoder):
    """ JSON编码器：外层结构保持缩进，但所有纯基本类型的叶子列表（含None）强制单行输出 """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._indent = kwargs.get('indent', None)

    def is_leaf_list(self, lst):
        """判断列表是否为叶子列表（所有元素都是基本类型）"""
        return all(isinstance(x, (int, float, str, bool, type(None))) for x in lst)

    def default(self, o):
        # 仅当遇到 LeafList 且是叶子列表时触发错误
        if isinstance(o, LeafList) and self.is_leaf_list(o.lst):
            raise SyntaxError("LeafList detected in default method")
        return super().default(o)

# 测试用例数据（使用自定义 LeafList，不再继承 list）
test_data = {
    "short_list": LeafList([1, 2, 3]),
    "long_list": LeafList(list(range(1000))),
    "text_list": LeafList(["超长文本" * 50, "another"]),
    "mixed": [1, {"a": 2}, 3],  # 混合类型不会触发
    "none_list": LeafList([None, None, None]),
    "bool_list": LeafList([True, False, True]),
    "deep_nested": [
        {"key": LeafList([1, 2, 3, {"nested": "value"}])},
        LeafList([4, 5, 6])
    ]
}

def test_compact_encoder():
    """测试 CompactLeafListEncoder 是否能正确工作"""
    try:
        json_str = json.dumps(
            test_data, 
            cls=CompactLeafListEncoder,
            indent=2
        )
        print("✅ 执行 json.dumps 成功：CompactLeafListEncoder 没有被调用")
        print("生成的JSON内容:")
        lines = json_str.split('\n')
        print('\n'.join(lines[:min(10,len(lines))]))
        return False
    except SyntaxError as e:
        print(f"❌ 执行 json.dumps 失败: {e}")
        print("注意: 如果看到此错误，说明 CompactLeafListEncoder 的 default 方法被正确调用了")
        return True
    except Exception as e:
        print(f"❌ 执行 json.dumps 失败: 未知异常 {e}")
        return False

if __name__ == "__main__":
    print("开始测试 CompactLeafListEncoder (调用时故意报 SyntaxError 错误)")
    print("注意: 如果实现正确，将触发 SyntaxError 以验证编码器被正确调用")
    result = test_compact_encoder()
    print(f"测试结果: {'✅达成目标' if result else '❌未达成目标'}")