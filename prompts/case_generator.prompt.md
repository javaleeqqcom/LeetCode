你是一名计算机教育专家，请根据如下题目和学生代码写出一个测试数据生成器。

题目：
{question}

学生代码：
{student_code}

生成算法测试数据生成器，要求：

- 输出必须 JSON 可序列化
- 只输出 Python 代码
- scale 表示测试规模，应与学生代码执行时间基本成正比
- 禁止生成 main
- 注意依赖库要 import
- `case_generator` 只能返回测试输入：`{{"input": tuple|dict}}`；禁止返回 `output`、`cid`、日志或解释
- `scale` 可能是浮点数，涉及长度或 `range` 前必须转为整数
- 每一次随机生成都必须满足题目全部约束。若题目保证答案存在或唯一，应先构造合法答案，再填充不会产生额外答案的随机噪声；禁止把相互依赖的参数完全独立随机化
- 生成器自身必须为 O(n) 或 O(n log n)，禁止枚举所有元素对/组合，禁止 `while True` 拒绝采样；要通过构造法直接保证约束
- 不要输出示例调用、`if __name__ == "__main__"` 或 Markdown 代码围栏

请参考示例代码：
{case_generator_code}

测试策略：

{analysis}

其他模块代码参考（格式可能需要调整）：

{rag_context}
