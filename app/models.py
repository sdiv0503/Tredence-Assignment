from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class WorkflowState(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)
    history: List[str] = Field(default_factory=list)

class EdgeDefinition(BaseModel):
    source: str
    target: Optional[str] = None  # Make target optional for conditional edges
    condition: Optional[str] = None # The key to check in state (e.g., "status")
    mapping: Optional[Dict[str, Optional[str]]] = None # The map: {"continue": "node_x", "stop": None}

class GraphCreateRequest(BaseModel):
    nodes: List[str]
    edges: List[EdgeDefinition]
    start_node: str

class GraphRunRequest(BaseModel):
    graph_id: str
    initial_state: Dict[str, Any]