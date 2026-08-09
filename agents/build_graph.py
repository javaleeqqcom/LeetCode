from langgraph.graph import StateGraph
from agents.analyze_agent import AnalyzeAgent
from agents.case_generator_agent import CaseGeneratorAgent
from agents.graph_state import AgentState

def analyze_node(state: AgentState):
    problem = state["problem"]
    if problem is None:
        raise ValueError("AgentState.problem 不能为空")
    analysis = AnalyzeAgent().run(problem)
    problem.solution_struct.complexity_hint.time_complexity = analysis.complexity.time_complexity
    problem.solution_struct.complexity_hint.space_complexity = analysis.complexity.space_complexity
    return {"analysis": analysis}

def retrieve_node(state: AgentState):
    # 在这个节点里，我们可以把 analysis.knowledge_requirements 存入 state 便于后续使用
    return {
        "retrieved_case_context": "\n".join(state["analysis"].knowledge_requirements)
    }

def generate_case_node(state: AgentState):
    problem = state["problem"]
    if problem is None:
        raise ValueError("AgentState.problem 不能为空")
    # 将 complexity_hint 等信息事先填入 problem.solution_struct
    # 这里假设 complexity 已在 analyze 阶段填入，或由 ComplexityAnalyzer 预处理
    generated_code = CaseGeneratorAgent(problem).run()
    return {"generated_case_code": generated_code}

builder = StateGraph(AgentState)
builder.add_node("analyze", analyze_node)
builder.add_node("retrieve", retrieve_node)
builder.add_node("generate_case", generate_case_node)

builder.set_entry_point("analyze")
builder.add_edge("analyze", "retrieve")
builder.add_edge("retrieve", "generate_case")
builder.set_finish_point("generate_case")

graph = builder.compile()
