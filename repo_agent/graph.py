from langgraph.graph import END, StateGraph

from repo_agent.agent import handle_user_task
from repo_agent.context_engine import build_basic_context
from repo_agent.graph_state import AgentGraphState
from repo_agent.session import RepoSession
from repo_agent import display
from repo_agent.plan import create_plan, parse_plan_steps
from repo_agent.verifier import verify_working_tree

def build_agent_graph(repo_session: RepoSession):
    graph = StateGraph(AgentGraphState)

    def build_context_node(state: AgentGraphState) -> AgentGraphState:
        display.agent_step("build_context", "collecting repo files, git status, diff")
        context = build_basic_context(state['task'], repo_session)
        return {"context": context}
    
    def plan_node(state: AgentGraphState) -> AgentGraphState:
        display.agent_step("plan", "creating execution plan")
        plan = create_plan(state['task'], state.get('context', ''), repo_session)
        plan_steps = parse_plan_steps(plan)
        display.plan_checklist(plan_steps)
        return {"plan": plan, "plan_steps": plan_steps}
    
    def verify_node(state: AgentGraphState) -> AgentGraphState:
        display.agent_step("verify", "verifying execution plan")
        verification_report = verify_working_tree(repo_session)
        display.verification_report(verification_report)
        return {"verification": verification_report}


    def act_node(state: AgentGraphState) -> AgentGraphState:
        plan_steps = [dict(step) for step in state.get("plan_steps", [])]

        if plan_steps:
            plan_steps[0]["status"] = "in_progress"
            display.plan_checklist(plan_steps, title="Plan Progress")


        task_with_context = f"""Use this repository context to answer the task.

Repository Context:
{state["context"]}

Execution Plan:
{state["plan"]}

Task:
{state["task"]}
"""
        result = handle_user_task(task_with_context, repo_session)

        completed_steps = [
            {**step, "status": "completed"}
            for step in plan_steps
        ]

        display.plan_checklist(completed_steps, title="Plan Completed")
        return {"result": result, "plan_steps": completed_steps}
    
    graph.add_node("build_context", build_context_node)
    graph.add_node("act", act_node)
    graph.add_node("plan", plan_node)
    graph.add_node("verify", verify_node)
    graph.set_entry_point("build_context")
    graph.add_edge("build_context", "plan")
    graph.add_edge("plan", "act")
    graph.add_edge("act", "verify")
    graph.add_edge("verify", END)

    return graph.compile()

def run_graph_agent(task: str, repo_session: RepoSession) -> str:
    app = build_agent_graph(repo_session)
    result = app.invoke({"task": task})
    return result["result"]


