import json
class CompactLeafListEncoder(json.JSONEncoder):
    """
    JSON编码器：外层结构保持缩进，但所有纯基本类型的叶子列表（含None）强制单行输出
    - 无长度限制：超长列表也合并为单行（依赖编辑器自动换行）
    - 无字符串截断：完整保留原始内容
    - 精确判断：仅当列表所有元素均为 (int/float/str/bool/None) 时视为叶子列表
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._indent = kwargs.get('indent', None)
    
    def default(self, o):
        # 用于验证 CompactLeafListEncoder 是否被正确调用
        raise SyntaxError("CompactLeafListEncoder.default() is working!")
        return super().default(o)

# 测试用例数据
test_data = {
    "short_list": [1, 2, 3],
    "long_list": list(range(1000)),  # 1000个数字
    "text_list": ["超长文本" * 50, "another"],
    "mixed": [1, {"a": 2}, 3],
    "none_list": [None, None, None],
    "bool_list": [True, False, True],
    "deep_nested": [
        {"key": [1, 2, 3, {"nested": "value"}]},
        [4, 5, 6]
    ]
}

def test_compact_encoder():
    """测试 CompactLeafListEncoder 是否能正确工作"""
    try:
        # 尝试使用自定义编码器
        json_str = json.dumps(
            test_data,
            cls=CompactLeafListEncoder,
            indent=2,
            ensure_ascii=False
        )
        print("✅ 执行 json.dumps 成功：CompactLeafListEncoder 没有被调用")
        print("生成的JSON内容:")
        print(json_str[:10] + "..." if len(json_str) > 10 else json_str)
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