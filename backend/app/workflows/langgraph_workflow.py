# workflows/langgraph_workflow.py
import logging
from typing import Literal

from langgraph.graph import StateGraph, END
from app.state.graph_state import GraphState
from app.agents.supervisor_agent import SupervisorAgent
from app.tools.rag_tools import pgvector_search, generate_summary, llm_service

logger = logging.getLogger(__name__)

# Initialize supervisor with fast heuristic routing
supervisor = SupervisorAgent(llm_service=llm_service, use_llm_routing=False)

# Node Definitions
async def supervisor_node(state: GraphState):
    logger.info("LangGraph: Entering supervisor_node")
    route = await supervisor.decide_route(state["user_message"])
    return {"route": route}

async def greeting_node(state: GraphState):
    logger.info("LangGraph: Entering greeting_node")
    greeting_reply = (
        "Hello, bonjour — how can I help you?\n\n"
        "You can ask me to summarize a topic, search the indexed knowledge base, "
        "or do both in parallel."
    )
    return {"final_answer": greeting_reply}

async def search_node(state: GraphState):
    logger.info("LangGraph: Entering search_node")
    # Execute LangChain tool
    result = await pgvector_search.ainvoke({
        "query": state["user_message"], 
        "user_id": str(state["user_id"]), 
        "file_ids": state.get("file_ids")
    })
    
    update = {"search_output": result}
    # Direct search return
    if state.get("route") == "search":
        update["final_answer"] = result
        
    return update

async def summary_node(state: GraphState):
    logger.info("LangGraph: Entering summary_node")
    # Bypass redundant summary LLM call in parallel route to cut 1 full LLM roundtrip
    if state.get("route") == "parallel":
        logger.info("LangGraph: Skipping redundant summary LLM call in parallel route")
        return {"summary_output": ""}

    # Execute LangChain tool for direct summary route
    result = await generate_summary.ainvoke({"prompt": state["user_message"]})
    
    update = {"summary_output": result}
    # Direct summary return
    if state.get("route") == "summary":
        update["final_answer"] = result
        
    return update

async def grounded_generation_node(state: GraphState):
    logger.info("LangGraph: Entering grounded_generation_node")
    
    search_output = state.get("search_output", "")
    summary_output = state.get("summary_output", "")
    conversation_context = state.get("conversation_context", [])
    
    conversation_history = "\n".join(
        f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
        for msg in conversation_context
    )
    
    grounded_context = (
        f"{search_output}\n\n"
        f"Draft summary:\n{summary_output}\n\n"
    )
    
    try:
        grounded_answer = await llm_service.grounded_answer(
            question=state["user_message"],
            retrieved_documents=grounded_context,
            conversation_history=conversation_history,
        )
        return {
            "final_answer": grounded_answer.strip(),
            "model_used": llm_service.last_used_model
        }
    except Exception as exc:
        logger.error(f"Grounded generation failed: {exc}")
        return {
            "final_answer": f"Grounded generation failed: {exc}\nFallback Summary: {summary_output}",
            "model_used": llm_service.last_used_model
        }


# Conditional Routing Functions
def route_after_supervisor(state: GraphState):
    route = state["route"]
    if route == "greeting":
        return "greeting_node"
    elif route == "search":
        return "search_node"
    elif route == "summary":
        return "summary_node"
    elif route == "parallel":
        return ["search_node", "summary_node"]
    return "parallel"

def route_after_branch(state: GraphState) -> Literal["grounded_generation_node", "__end__"]:
    # Using LangGraph END representation
    if state["route"] == "parallel":
        return "grounded_generation_node"
    return END

# Build the Graph
builder = StateGraph(GraphState)

# Add Nodes
builder.add_node("supervisor_node", supervisor_node)
builder.add_node("greeting_node", greeting_node)
builder.add_node("search_node", search_node)
builder.add_node("summary_node", summary_node)
builder.add_node("grounded_generation_node", grounded_generation_node)

# Add Edges
builder.set_entry_point("supervisor_node")

builder.add_conditional_edges(
    "supervisor_node",
    route_after_supervisor,
    ["greeting_node", "search_node", "summary_node"]
)

builder.add_conditional_edges("search_node", route_after_branch)
builder.add_conditional_edges("summary_node", route_after_branch)

builder.add_edge("greeting_node", END)
builder.add_edge("grounded_generation_node", END)

# Compile Application
app = builder.compile()
