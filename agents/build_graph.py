from langgraph.graph import StateGraph

from graph.state import AgentState

from agents.analyze_agent import AnalyzeAgent


analyze_agent = AnalyzeAgent()


def analyze_node(state: AgentState):

    analysis = analyze_agent.run(
        question=state["question_text"],
        student_code=state["student_code"],
        language=state["file_suffix"],
    )

    return {
        "analysis": analysis
    }


builder = StateGraph(AgentState)

builder.add_node(
    "analyze",
    analyze_node
)

builder.set_entry_point("analyze")

builder.set_finish_point("analyze")

graph = builder.compile()