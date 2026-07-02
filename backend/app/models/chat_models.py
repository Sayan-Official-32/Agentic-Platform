# models/chat_models.py
# This module defines the schemas used for the chat system.
# It defines request/response contracts for the chat HTTP endpoints and structures to hold 
# intermediate data like search hits, agent logs, and conversation lists.

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """
    Represents a single message in a chat history sequence.
    'role' determines the sender, constrained by 'Literal' to be 'user', 'assistant', or 'system'.
    'content' is the text body of the message.
    """
    role: Literal["user", "assistant", "system"]
    content: str
    
class ChatRequest(BaseModel):
    """
    Request model sent by the frontend client to talk to our multi-agent system.
    'message' is the user's new question/prompt.
    'conversation_id' is optional. If provided, we resume that chat; if not, we generate a new UUID.
    'history' is the array of previous ChatMessage interactions so the agents remember the context.
    """
    message: str = Field(min_length=1)
    conversation_id: Optional[str] = None
    history: List[ChatMessage] = Field(default_factory=list)
    
class SearchResult(BaseModel):
    """
    Structured document snippet hit retrieved from Elasticsearch during a search operation.
    'title': Document title/section.
    'snippet': Matching text fragment.
    'score': Relevance score assigned by Elasticsearch's search engine.
    'source': Source type (e.g. 'elasticsearch').
    'page_number': Source page number if parsed from a PDF.
    'file_name': Source file name.
    """
    title: str
    snippet: str
    score: float
    source: str
    page_number: Optional[int] = None
    file_name: Optional[str] = None

class AgentResult(BaseModel):
    """
    Logs the output of a specific agent (e.g., 'search', 'summary') during execution.
    Helps the frontend display which agents ran, what they found, and any extra metadata.
    """
    agent: str
    output: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatResponse(BaseModel):
    """
    Final JSON response sent back to the client after the multi-agent workflow completes.
    'conversation_id': The UUID associated with this conversation.
    'route': The final route chosen by the supervisor ('greeting', 'search', 'summary', etc.).
    'answer': The formatted response text to display to the user.
    'agents_used': List of agent names that participated in generating the response.
    'agent_results': Detailed logs of what each agent returned.
    'cached': True if the response was retrieved from Redis cache directly, avoiding LLM/Search execution.
    'context_messages': Number of messages currently stored in the conversation's memory.
    """
    conversation_id: str
    route: str
    answer: str
    agents_used: List[str]
    agent_results: List[AgentResult]
    cached: bool = False
    context_messages: int = 0

class ConversationContextResponse(BaseModel):
    """
    Response model returning the raw history stored in Redis memory for a given conversation_id.
    """
    conversation_id: str
    message_count: int
    messages: List[Dict[str, str]]