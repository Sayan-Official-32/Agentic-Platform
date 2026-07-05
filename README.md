# 🤖 Agentic AI Chat System

**A production-grade, multi-agent cooperative RAG platform that actually works.**

---

[![FastAPI Version](https://img.shields.io/badge/FastAPI-0.137.2-green.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js Version](https://img.shields.io/badge/Next.js-15.2.4-black.svg?style=flat&logo=next.js)](https://nextjs.org)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat&logo=python)](https://python.org)
[![Node Version](https://img.shields.io/badge/Node.js-%3E%3D18.0.0-green.svg?style=flat&logo=node.js)](https://nodejs.org)
[![Docker Support](https://img.shields.io/badge/Docker-Supported-blue.svg?style=flat&logo=docker)](https://www.docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 1. Project Overview

The **Agentic AI Chat System** is an enterprise-ready Retrieval-Augmented Generation (RAG) platform. Built around a dynamic multi-agent supervisor graph, it coordinates specialized micro-agents to resolve user requests with high grounding accuracy and low latency.

### Why this project?
1. **Adaptive Query Execution**: Rather than using a static search-and-generate loop, the system routes queries through a **Supervisor Agent** to determine the optimal workflow (e.g., direct chat, fast search, general summary, or parallel RAG).
2. **Mitigating Hallucinations**: Leverages grounded answer generation models that strictly synthesize output using source document context retrieved from a vector index, complete with page-level and file-name attributions.
3. **Resilient Local & Cloud Integrations**: Runs light, free, and privacy-first local models (via Ollama) or scales to powerful serverless inference backends (via Hugging Face Router API).
4. **Local Embedding & Reranking**: Generates embeddings locally using SentenceTransformers (`sentence-transformers/all-MiniLM-L6-v2`) and reranks results via a CrossEncoder model (`cross-encoder/ms-marco-MiniLM-L-6-v2`) for state-of-the-art precision.

---

## 🚀 2. Features

### Core AI & Agent Features
* **Supervisor Agent**: Employs hybrid routing—fast keyword heuristics or precise LLM semantic analysis—to orchestrate tasks.
* **Parallel RAG Execution**: Runs database search and summary agent threads concurrently to minimize response latency.
* **Cross-Encoder Reranking**: Automatically reranks candidates before synthesis, ensuring high relevance of RAG context.
* **Grounded Synthesis**: Guarantees source-attributed answers with exact page numbers and document names.

### Security & Performance
* **JWT Identity Protection**: Secures routes with stateless token verification and encrypted bcrypt password hashing.
* **Token-Bucket Rate Limiting**: Intercepts backend API requests to prevent abuse (default 60 req/minute).
* **High-Performance Caching**: Caches final response payloads, query embeddings, and message history logs inside Redis Stack.
* **Resilient Client Services**: Auto-reconnects to Redis and Supabase if databases restart during runtime.

---

## 🎨 3. Interactive Demo & Preview

The dashboard UI provides a high-fidelity workspace showing chat histories, document management, and real-time backend telemetry metrics.

| Interactive Console Dashboard |
| :---: |
| ![Chat Interface](gitimg/1.png) |

### Key Sections of the Demo
* **Document Explorer (Sidebar)**: Upload and manage documents. Supported file formats include `.pdf`, `.csv`, `.docx`, `.txt`, `.xlsx`, `.pptx`, `.html`, `.json`, and `.md`. You can scoped your queries to search across specific files.
* **Suggested Questions**: Dynamically generates sample questions based on newly uploaded files using the LLM.
* **Dynamic Agent Logs**: Visualizes exactly how the multi-agent graph runs. View the supervisor decision, raw search output, summary blocks, and grounded answer inputs under collapsible accordions.
* **Telemetry Monitors**: Real-time performance monitors showing Redis cache states, Supabase DB latency, API response times, and model parameter indicators.

---

## 📐 4. System Architecture

The following diagram details the flow of data from the frontend Next.js interface down to the micro-agents, embedding generation, rerankers, and databases:

```mermaid
graph TD
    User([End User]) -->|HTTPS / JWT| FE[Next.js Frontend]
    FE -->|REST API| BE[FastAPI Backend]

    subgraph FastAPI Service Routing
        BE -->|Auth Verification| Token[Token Service]
        BE -->|Workflows| WF[Chat Workflow Executor]
        
        WF -->|Routing Query| SV[Supervisor Agent]
        SV -->|Route: greeting| G[Greeting Handler]
        SV -->|Route: search| SA[Search Agent]
        SV -->|Route: summary| SU[Summary Agent]
        SV -->|Route: parallel| PA[Parallel Executive Node]

        PA -->|Parallel Task| SA & SU
        SA -->|Vector Lookup| DBClient[Search Service]
        SU -->|Context Summary| LLMClient[LLM Service]
        
        DBClient -->|Local Embeddings| Embed[SentenceTransformers]
        DBClient -->|Rerank Candidates| Reranker[CrossEncoder Model]
    end

    subgraph Databases & Providers
        DBClient -->|pgvector Cosine Search| Supabase[(Supabase DB)]
        LLMClient -->|API Completions| LLM[HF Router / Local Ollama]
        BE -->|Cache & Session Memory| Redis[(Redis Stack)]
    end
```

---

## 🛠️ 5. Technology Stack

| Component | Selected Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS | Responsive dashboard console & client session handling. |
| **Backend** | FastAPI, Pydantic, Uvicorn | High-performance async ASGI gateway and router. |
| **Storage & DB**| Supabase (PostgreSQL + pgvector) | Document metadata, vector embeddings storage, and file storage bucket. |
| **Cache & Memory**| Redis Stack, Redis Insight | Session history list, API caching, embedding cache, and GUI monitoring. |
| **AI Framework** | Hugging Face Router / Ollama API | Multi-model OpenAI spec inference wrapper. |
| **Local Models** | SentenceTransformers & CrossEncoder | Local vector embedding (`all-MiniLM-L6-v2`) and reranking (`ms-marco-MiniLM-L-6-v2`). |
| **Observability**| Langfuse (Optional) | End-to-end LLM call tracing, evaluations, and latency logs. |

---

## 💻 6. Installation & Local Setup

### Step 1: Start Databases (Docker)
Ensure Docker is installed and running, then start the Redis service:
```bash
docker compose up -d
```
Verify Redis dashboard is active at: **[http://localhost:8001](http://localhost:8001)**

### Step 2: Configure & Run Backend (FastAPI)
> [!IMPORTANT]
> All Python and backend execution commands **MUST** be run strictly inside the activated virtual environment (`venv`).

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Copy the environment template:
   ```bash
   copy .env.example .env
   # Or "cp .env.example .env" on Linux/macOS
   ```
3. Set your Hugging Face API key and Supabase Credentials in `.env`:
   ```env
   HUGGINGFACE_API_KEY=hf_your_key_here
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_KEY=your-service-role-key
   ```
4. Create and activate a Python virtual environment:
   ```bash
   # Windows Command Prompt:
   python -m venv venv
   venv\Scripts\activate

   # Windows PowerShell:
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux/macOS:
   python3 -m venv venv
   source venv/bin/activate
   ```
5. Install dependencies and start the server:
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

### Step 3: Run Frontend (Next.js)
1. Open a new terminal tab/window and navigate to the frontend:
   ```bash
   cd frontend
   ```
2. Setup environment settings and install dependencies:
   ```bash
   copy .env.example .env.local
   # Or "cp .env.example .env.local" on Linux/macOS
   
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
4. Access the workspace at: **[http://localhost:3000](http://localhost:3000)**

---

## 🌐 7. Production Deployment Guide

Deploying this multi-agent application to production requires hosting the Next.js frontend, FastAPI backend, Supabase DB, and a Redis cluster.

### 1. Database & Ingestion Setup (Supabase)
1. **Create a Supabase Project**: Sign up on [Supabase](https://supabase.com) and spin up a new PostgreSQL project.
2. **Enable pgvector**: Run the migration SQL files located in `backend/supabase/migrations` sequentially under the **SQL Editor** tab of your Supabase dashboard to enable vector extensions and create tables (`users`, `user_files`, `document_chunks`, `conversation_sessions`, `conversation_messages`, and `match_document_chunks` RPC function).
3. **Storage Bucket**: Create a new storage bucket named `user-documents` in Supabase. Set its visibility based on security needs (private is recommended).

### 2. Caching Setup (Upstash Redis)
1. Register on [Upstash](https://upstash.com) or [Redis Cloud](https://redis.com) to create a serverless Redis database.
2. Retrieve the `REDIS_URL` connection string (e.g., `rediss://default:your-password@your-endpoint.upstash.io:6379`).

### 3. Deploy Backend API (FastAPI)
You can deploy the backend to platforms like **Railway**, **Render**, **Fly.io**, or **Hugging Face Spaces**.
* **Dockerfile**: Create a Dockerfile in `/backend` to containerize the FastAPI service.
* **Environment Variables**:
  * `LLM_PROVIDER=huggingface`
  * `HUGGINGFACE_API_KEY=hf_your_production_token`
  * `REDIS_URL=rediss://default:password@endpoint:port`
  * `SUPABASE_URL=https://your-production-project.supabase.co`
  * `SUPABASE_SERVICE_KEY=your-service-role-key`
  * `SUPABASE_STORAGE_BUCKET=user-documents`
  * `BACKEND_CORS_ORIGINS=https://your-frontend.vercel.app`
  * `AUTH_SECRET_KEY=long-random-cryptographic-string-here`

### 4. Deploy Frontend (Next.js on Vercel)
1. Connect your GitHub repository to **Vercel**.
2. Set the root directory of the Vercel project to `frontend/`.
3. Configure the environment variable:
   * `NEXT_PUBLIC_BACKEND_URL=https://your-backend-api.onrender.com`
4. Click **Deploy**.

---

## 🔑 8. Environment Variables (`backend/.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | `huggingface` | AI completion gateway (`huggingface` or `ollama`). |
| `HUGGINGFACE_API_KEY` | `""` | Access Token with Serverless Inference API permissions. |
| `MODEL_SUMMARIZATION` | `deepseek-ai/DeepSeek-V4-Pro` | Model used for text summarization. |
| `MODEL_QUESTION_ANSWERING` | `Qwen/Qwen2.5-7B-Instruct` | Model used for grounded responses. |
| `REDIS_URL` | `redis://:redis_password@localhost:6379/0` | Connection URI for the Redis cache. |
| `SUPABASE_URL` | `""` | Endpoint for the Supabase database. |
| `SUPABASE_SERVICE_KEY` | `""` | Service role API key for Supabase client. |
| `SUPABASE_STORAGE_BUCKET`| `user-documents` | Name of the Supabase storage bucket. |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model loaded locally. |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Sentence reranker loaded locally. |

---

## 🌐 9. API Reference

| Endpoint | Method | Authentication | Description |
| :--- | :--- | :--- | :--- |
| `/health` | `GET` | None | Returns database connectivity status. |
| `/api/v1/auth/register` | `POST` | None | Registers a new user email and password. |
| `/api/v1/auth/login` | `POST` | None | Authenticates credentials and returns a JWT. |
| `/api/v1/ingest/upload` | `POST` | Bearer Token | Uploads a document to storage and indexes it. |
| `/api/v1/ingest/sample-data`| `POST` | Bearer Token | Ingests the default `data/ai_tooling_catalog.csv` file. |
| `/api/v1/files` | `GET` | Bearer Token | Lists all uploaded user files. |
| `/api/v1/files/{file_id}` | `DELETE` | Bearer Token | Deletes a file, its storage object, and vector chunks. |
| `/api/v1/chat` | `POST` | Bearer Token | Submits user message to the agent executor. |

---

## 🛡️ 10. Security & Threat Mitigation
1. **Stateless JWT Guard**: Employs industry-standard JWT authentication for securing API endpoints.
2. **Password Cryptography**: Passwords are securely hashed using `bcrypt` (salted iterations) inside the Auth service before database storage.
3. **CORS Restrictions**: API access is restricted to whitelisted frontend domains.
4. **Client Isolation**: All document chunks and vector query calls are scoped tightly to the authenticated user ID.

---

## 📜 11. License & Acknowledgments

This project is open-source and licensed under the [MIT License](LICENSE). 

Special thanks to the developers of **FastAPI**, **Next.js**, **Hugging Face**, **Redis**, and **Supabase** for providing the core building blocks of this agentic chat ecosystem.