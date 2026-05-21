from langgraph.graph import END, StateGraph

from repo_agent.agent import handle_user_task
from repo_agent.context_engine import build_basic_context
from repo_agent.graph_state import AgentGraphState
from repo_agent.session import RepoSession
from repo_agent import display
from repo_agent.plan import create_plan, parse_plan_steps
from repo_agent.verifier import verify_working_tree
from repo_agent.summarizer import summarize_agent_run
from repo_agent.executor import execute_plan_step

"""
help function for formatting step results into a readable summary
"""
def format_step_results(step_results: list[dict[str, str]]) -> str:
    if not step_results:
        return "No step results."

    sections: list[str] = []

    for index, item in enumerate(step_results, start=1):
        status = item.get("status", "completed")
        step = item.get("step", "")
        result = item.get("result", "")

        sections.append(
            f"""Step {index}: {status}
Task: {step}

Result:
{result}"""
        )

    return "\n\n".join(sections)




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


#     def act_node(state: AgentGraphState) -> AgentGraphState:
#         plan_steps = [dict(step) for step in state.get("plan_steps", [])]

#         if plan_steps:
#             plan_steps[0]["status"] = "in_progress"
#             display.plan_checklist(plan_steps, title="Plan Progress")


#         task_with_context = f"""Use this repository context to answer the task.

# Repository Context:
# {state["context"]}

# Execution Plan:
# {state["plan"]}

# Task:
# {state["task"]}
# """
#         result = handle_user_task(task_with_context, repo_session)

#         completed_steps = [
#             {**step, "status": "completed"}
#             for step in plan_steps
#         ]

#         display.plan_checklist(completed_steps, title="Plan Completed")
#         return {"result": result, "plan_steps": completed_steps}
    

    """
    New act node with step-by-step execution and verification after each step. The agent will execute one step, verify the working tree, and update the plan checklist accordingly. If a step fails (i.e. the working tree is dirty after execution), it will mark that step as failed and stop further execution.
    """
    def act_node(state: AgentGraphState) -> AgentGraphState:
        display.agent_step("act", "executing plan steps with verification")

        plan_steps = [dict(step) for step in state.get("plan_steps", [])]
        step_results: list[dict[str, str]] = []
        completed_results: list[str] = []

        if not plan_steps:
            result = execute_plan_step(
                task=state["task"],
                context=state.get("context", ""),
                plan=state.get("plan", ""),
                current_step=state["task"],
                completed_results=completed_results,
                repo_session=repo_session,
            )
            return {
            "result": result,
            "step_results": [
                {
                    "step": state["task"],
                    "status": "completed",
                    "result": result,
                }
            ]
        }
        for index, step in enumerate(plan_steps):
            current_step = step.get("text", "").strip()
            if not current_step:
                step["status"] = "skipped"
                continue

            plan_steps[index]["status"] = "in_progress"
            display.plan_checklist(plan_steps, title="Plan Progress")

            try:
                step_result = execute_plan_step(
                    task=state["task"],
                    context=state.get("context", ""),
                    plan=state.get("plan", ""),
                    current_step=current_step,
                    completed_results=completed_results,
                    repo_session=repo_session,
                )
            except Exception as e:
                error_message = f"Error executing step: {e}"
                plan_steps[index]["status"] = "failed"
                step_results.append({
                    "step": current_step,
                    "status": "failed",
                    "result": error_message,
                })
                display.plan_checklist(plan_steps, title="Plan Progress")
                return {
                    "result": error_message,
                    "step_results": step_results,
                    "plan_steps": plan_steps,
                }
            
            plan_steps[index]["status"] = "completed"
            completed_results.append(step_result)
            step_results.append({
                "step": current_step,
                "status": "completed",
                "result": step_result,
            })

            display.plan_checklist(plan_steps, title="Plan Progress")

        display.plan_checklist(plan_steps, title="Plan Completed")

        return {
            "result": format_step_results(step_results),
            "step_results": step_results,
            "plan_steps": plan_steps,
        }


    

    """
    Summarize the agent's execution and results, and suggest next steps or a commit message if applicable.
    """
    def summarize_node(state: AgentGraphState) -> AgentGraphState:
        display.agent_step("summarize", "summarizing agent run")
        summary = summarize_agent_run(
            task=state['task'],
            plan=state.get('plan', ''),
            result=state.get('result', ''),
            verification_report=state.get('verification', {}),
        )
        return {"summary": summary}
    
    graph.add_node("build_context", build_context_node)
    graph.add_node("act", act_node)
    graph.add_node("plan", plan_node)
    graph.add_node("verify", verify_node)
    graph.add_node("summarize", summarize_node)
    graph.set_entry_point("build_context")
    graph.add_edge("build_context", "plan")
    graph.add_edge("plan", "act")
    graph.add_edge("act", "verify")
    graph.add_edge("verify", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()

def run_graph_agent(task: str, repo_session: RepoSession) -> str:
    app = build_agent_graph(repo_session)
    result = app.invoke({"task": task})
    return result.get("summary", "No summary generated.") or result.get("result", "No result generated.")   



