# API Endpoint Specification

All REST API endpoints are prefixed with `/api/v1`.

---

## 1. Authentication Endpoints

### `POST /api/v1/auth/register`
Registers a new user account.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "SecretPassword123"
  }
  ```
- **Response**: `200 OK` with user details.

### `POST /api/v1/auth/login`
Authenticates user credentials and issues a JWT token.
- **Request Body**: Same as register.
- **Response**:
  ```json
  {
    "access_token": "eyJhbGci...",
    "token_type": "bearer",
    "email": "user@example.com"
  }
  ```

---

## 2. Ingestion & File Management Endpoints

### `POST /api/v1/ingest/upload`
Uploads a document (`.pdf`, `.docx`, `.txt`, `.csv`, `.xlsx`, `.pptx`, `.html`, `.json`, `.md`), chunks it using LangChain, generates local embeddings, and indexes chunks in Supabase `pgvector`.
- **Headers**: `Authorization: Bearer <JWT>`
- **Query Params**: `conversation_id` (optional)
- **Form Data**: `file`
- **Response**:
  ```json
  {
    "file_id": "uuid",
    "file_name": "report.pdf",
    "chunks_created": 12,
    "status": "ready"
  }
  ```

### `GET /api/v1/files`
Lists all uploaded files owned by the user.
- **Headers**: `Authorization: Bearer <JWT>`

### `DELETE /api/v1/files/{file_id}`
Deletes a file, its storage bucket object, and its indexed vector chunks.
- **Headers**: `Authorization: Bearer <JWT>`

---

## 3. Conversation & Chat Endpoints

### `GET /api/v1/conversations`
Retrieves all conversation sessions owned by the user.

### `POST /api/v1/conversations`
Creates a new conversation session.

### `DELETE /api/v1/conversations/{session_id}`
Deletes a conversation session and its message history.

### `POST /api/v1/chat`
Submits a query to the LangGraph multi-agent execution pipeline.
- **Headers**: `Authorization: Bearer <JWT>`
- **Request Body**:
  ```json
  {
    "message": "What are the key findings?",
    "conversation_id": "uuid-or-null",
    "history": [],
    "file_ids": ["uuid-1"]
  }
  ```
- **Response**:
  ```json
  {
    "conversation_id": "uuid",
    "route": "parallel",
    "answer": "Structured formal response text...",
    "agents_used": ["langgraph_router"],
    "agent_results": [],
    "cached": false,
    "context_messages": 4,
    "model_used": "Groq (llama-3.1-8b-instant)",
    "question": "What are the key findings?",
    "sources": "1. report.pdf (Page 1) — Chunk text..."
  }
  ```
