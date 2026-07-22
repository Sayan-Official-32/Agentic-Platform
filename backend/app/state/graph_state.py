from uuid import UUID
from typing import Dict, List, Optional, TypedDict

from app.models.chat_models import ChatMessage, SearchResult
from app.models.file_models import ChunkResult

class GraphState(TypedDict, total=False):
    """
    GraphState holds the runtime data for a single user interaction cycle.
    As it passes through different nodes in the LangGraph, its fields are updated.
    """
    conversation_id: str                      
    user_message: str                         
    history: List[ChatMessage]                
    conversation_context: List[Dict[str, str]]
    
    route: str                                
    summary_output: str                       
    search_output: str                        
    search_results: Optional[List[SearchResult]]
    retrieved_chunks: List[ChunkResult]       
    reranked_chunks: List[ChunkResult]        
    final_answer: str                         
    user_id: Optional[UUID]                   
    file_ids: Optional[List[str]]             
    model_used: Optional[str]             