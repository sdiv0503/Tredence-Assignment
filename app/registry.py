from app.models import WorkflowState

TOOL_REGISTRY = {}

def register_tool(name):
    """A decorator to register functions into our registry automatically."""
    def decorator(func):
        TOOL_REGISTRY[name] = func
        return func
    return decorator

@register_tool("split_text")
def split_text(state: WorkflowState) -> WorkflowState:
    """Splits raw text into sentence chunks."""
    raw_text = state.data.get("text", "")
    
    chunks = [s.strip() for s in raw_text.split('.') if s.strip()]
    
    state.data["chunks"] = chunks
    print(f" -> [Tool] Split input into {len(chunks)} chunks.")
    return state

@register_tool("summarize_chunks")
def summarize_chunks(state: WorkflowState) -> WorkflowState:
    """Mock summarization: keeps the first 3 words of each chunk."""
    chunks = state.data.get("chunks", [])
    summaries = []
    
    for chunk in chunks:
        words = chunk.split()
        short_version = " ".join(words[:3]) + "..."
        summaries.append(short_version)
    
    state.data["chunk_summaries"] = summaries
    print(f" -> [Tool] Generated {len(summaries)} chunk summaries.")
    return state

@register_tool("merge_summaries")
def merge_summaries(state: WorkflowState) -> WorkflowState:
    """Combines all chunk summaries into one draft."""
    summaries = state.data.get("chunk_summaries", [])
    full_summary = " ".join(summaries)
    
    state.data["current_summary"] = full_summary
    state.data["summary_length"] = len(full_summary)
    
    print(" -> [Tool] Merged summaries.")
    return state

@register_tool("refine_summary")
def refine_summary(state: WorkflowState) -> WorkflowState:
    """
    Refines the summary if it is too long.
    Simulation: Removes the last word to shorten it iteratively.
    """
    current = state.data.get("current_summary", "")
    
    words = current.split()
    if len(words) > 0:
        words = words[:-1] 
        
    new_summary = " ".join(words)
    state.data["current_summary"] = new_summary
    state.data["summary_length"] = len(new_summary)
    
    if len(new_summary) > 50:
        state.data["status"] = "continue"
        print(f" -> [Tool] Refined (Len: {len(new_summary)}). Status: continue")
    else:
        state.data["status"] = "stop"
        print(f" -> [Tool] Refined (Len: {len(new_summary)}). Status: stop")
        
    return state