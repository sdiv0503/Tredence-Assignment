import asyncio
from typing import Dict, Callable, Any, Optional
from app.models import WorkflowState

NodeFunction = Callable[[WorkflowState], WorkflowState]

class WorkflowEngine:
    def __init__(self):
        self.nodes: Dict[str, NodeFunction] = {}
        self.edges: Dict[str, Any] = {} 
        self.start_node: Optional[str] = None

    def add_node(self, name: str, func: NodeFunction):
        self.nodes[name] = func

    def add_edge(self, source: str, target: str):
        self.edges[source] = target

    def add_conditional_edge(self, source: str, condition_key: str, mapping: Dict[Any, str]):
        self.edges[source] = {
            "type": "conditional",
            "key": condition_key,
            "mapping": mapping
        }

    def set_entry_point(self, node_name: str):
        self.start_node = node_name

    async def run(self, initial_payload: Dict[str, Any], step_callback=None):
        """
        Runs the graph. 
        If step_callback is provided (WebSocket), it streams logs.
        If not (REST), it just collects them.
        """
        state = WorkflowState(data=initial_payload)
        current_node_name = self.start_node
        
        logs = []
        step_count = 0
        MAX_STEPS = 50 

        while current_node_name and step_count < MAX_STEPS:
            log_msg = f"Step {step_count + 1}: Executing '{current_node_name}'"
            logs.append(log_msg)
            
            # --- HYBRID LOGIC ---
            # If connected via WebSocket, send update immediately
            if step_callback:
                await step_callback(log_msg)
                await asyncio.sleep(0.5) # Artificial delay to make the demo look cool
            # --------------------

            if current_node_name not in self.nodes:
                raise ValueError(f"Node '{current_node_name}' not found")
            
            node_func = self.nodes[current_node_name]
            
            if asyncio.iscoroutinefunction(node_func):
                state = await node_func(state)
            else:
                state = node_func(state)
            
            state.history.append(current_node_name)

            # Edge Logic
            edge_config = self.edges.get(current_node_name)
            if not edge_config:
                current_node_name = None
            elif isinstance(edge_config, str):
                current_node_name = edge_config
            elif isinstance(edge_config, dict) and edge_config.get("type") == "conditional":
                check_key = edge_config["key"]
                val = state.data.get(check_key)
                current_node_name = edge_config["mapping"].get(val)
            
            step_count += 1

        finish_msg = "Execution Finished"
        logs.append(finish_msg)
        if step_callback:
            await step_callback(finish_msg)
            
        return state, logs