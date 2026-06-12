from langgraph.graph import StateGraph
from agents.analyze_agent import AnalyzeAgent
from agents.case_generator_agent import CaseGeneratorAgent
from graph.state import AgentState

analyze_agent = AnalyzeAgent()
case_gen_agent = CaseGeneratorAgent()

def analyze_node(state: AgentState):
    problem = state["problem"]
    analysis = analyze_agent.run(problem)
    return {"analysis": analysis}

def retrieve_node(state: AgentState):
    # 在这个节点里，我们可以把 analysis.knowledge_requirements 存入 state 便于后续使用
    return {
        "retrieved_case_context": state["analysis"].knowledge_requirements
    }

def generate_case_node(state: AgentState):
    problem = state["problem"]
    # 将 complexity_hint 等信息事先填入 problem.solution_struct
    # 这里假设 complexity 已在 analyze 阶段填入，或由 ComplexityAnalyzer 预处理
    generated_code = case_gen_agent.run(problem)
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