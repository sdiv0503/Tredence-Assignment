import uuid
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from typing import Dict
from fastapi.middleware.cors import CORSMiddleware
from app.models import GraphCreateRequest, GraphRunRequest
from app.engine import WorkflowEngine
from app.registry import TOOL_REGISTRY

app = FastAPI(title="AI Intern Workflow Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (good for development)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (POST, GET, etc.)
    allow_headers=["*"],  # Allows all headers
)

GRAPHS: Dict[str, WorkflowEngine] = {}
RUNS: Dict[str, Dict] = {}

# --- REST ENDPOINTS ---

@app.post("/graph/create")
def create_graph(payload: GraphCreateRequest):
    engine = WorkflowEngine()
    for node_name in payload.nodes:
        if node_name not in TOOL_REGISTRY:
            raise HTTPException(status_code=400, detail=f"Tool {node_name} not found")
        engine.add_node(node_name, TOOL_REGISTRY[node_name])
    
    for edge in payload.edges:
        if edge.condition and edge.mapping:
            engine.add_conditional_edge(edge.source, edge.condition, edge.mapping)
        elif edge.target:
            engine.add_edge(edge.source, edge.target)

    engine.set_entry_point(payload.start_node)
    graph_id = str(uuid.uuid4())
    GRAPHS[graph_id] = engine
    return {"graph_id": graph_id, "message": "Graph created"}

@app.post("/graph/run")
async def run_graph(payload: GraphRunRequest, background_tasks: BackgroundTasks):
    """Standard Async REST Endpoint"""
    if payload.graph_id not in GRAPHS:
        raise HTTPException(status_code=404, detail="Graph ID not found")
    
    engine = GRAPHS[payload.graph_id]
    run_id = str(uuid.uuid4())
    RUNS[run_id] = {"status": "running", "state": None, "logs": []}

    async def _execute(r_id, eng, init_state):
        try:
            # Note: No callback here, just standard execution
            final_state, logs = await eng.run(init_state)
            RUNS[r_id]["status"] = "completed"
            RUNS[r_id]["state"] = final_state.dict()
            RUNS[r_id]["logs"] = logs
        except Exception as e:
            RUNS[r_id]["status"] = "failed"
            RUNS[r_id]["error"] = str(e)

    background_tasks.add_task(_execute, run_id, engine, payload.initial_state)
    return {"run_id": run_id, "status": "queued"}

@app.get("/graph/state/{run_id}")
def get_run_state(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run ID not found")
    return RUNS[run_id]

# --- WEBSOCKET ENDPOINT ---

@app.websocket("/ws/run")
async def websocket_run(websocket: WebSocket):
    """Real-time Streaming Endpoint"""
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        graph_id = data.get("graph_id")
        initial_state = data.get("initial_state")

        if not graph_id or graph_id not in GRAPHS:
            await websocket.send_text("Error: Graph ID not found")
            await websocket.close()
            return

        engine = GRAPHS[graph_id]

        # Define the callback to push logs to client
        async def stream_log(msg: str):
            await websocket.send_text(msg)

        await websocket.send_text(f"--- Connected to Graph {graph_id} ---")
        
        # Run with the callback
        final_state, logs = await engine.run(initial_state, step_callback=stream_log)
        
        await websocket.send_text("--- Run Complete ---")
        # Send final JSON result as text
        await websocket.send_text(str(final_state.dict()))
        
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.send_text(f"Error: {e}")
    finally:
        await websocket.close()

# --- DEMO LOADER ---
@app.on_event("startup")
def preload_demo_graph():
    demo_id = "demo-summary"
    engine = WorkflowEngine()
    engine.add_node("split_text", TOOL_REGISTRY["split_text"])
    engine.add_node("summarize_chunks", TOOL_REGISTRY["summarize_chunks"])
    engine.add_node("merge_summaries", TOOL_REGISTRY["merge_summaries"])
    engine.add_node("refine_summary", TOOL_REGISTRY["refine_summary"])
    
    engine.add_edge("split_text", "summarize_chunks")
    engine.add_edge("summarize_chunks", "merge_summaries")
    engine.add_edge("merge_summaries", "refine_summary")
    
    engine.add_conditional_edge("refine_summary", "status", {"continue": "refine_summary", "stop": None})
    engine.set_entry_point("split_text")
    GRAPHS[demo_id] = engine
    print(f"Graph ID: '{demo_id}' is ready.")