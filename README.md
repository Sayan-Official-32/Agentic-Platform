# 🤖 Agentic AI Platform

**An Enterprise-Grade, Multi-Agent RAG Platform Powered by LangGraph, FastAPI, Next.js, and Supabase.**

---

[![FastAPI Version](https://img.shields.io/badge/FastAPI-0.137.2-009688.svg?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js Version](https://img.shields.io/badge/Next.js-15.2.4-000000.svg?style=flat-square&logo=next.js)](https://nextjs.org)
[![LangChain / LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-1C3C3C.svg?style=flat-square&logo=langchain)](https://langchain.com)
[![Python Version](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?style=flat-square&logo=python)](https://python.org)
[![Supabase pgvector](https://img.shields.io/badge/Supabase-pgvector-3ECF8E.svg?style=flat-square&logo=supabase)](https://supabase.com)
[![AWS App Runner](https://img.shields.io/badge/AWS-App_Runner-FF9900.svg?style=flat-square&logo=amazon-aws)](https://aws.amazon.com/apprunner/)
[![Vercel Deployment](https://img.shields.io/badge/Vercel-Deployed-000000.svg?style=flat-square&logo=vercel)](https://vercel.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

---

## 📖 Executive Overview

The **Agentic AI Platform** is a production-ready Retrieval-Augmented Generation (RAG) ecosystem. Built on a dynamic **LangGraph `StateGraph` state machine**, it coordinates specialized micro-agents to execute user requests with low latency (~1–3s) and zero hallucination leakage.

### 🌟 Key Innovations
1. **LangGraph State Machine Orchestration**: Uses explicit state-driven graph execution with parallel branching (`search_node` + `summary_node` -> `grounded_generation_node`).
2. **Automated Multi-Provider LLM Failover**: Automatically cycles through **Groq** (`llama-3.1-8b-instant` ~500 tps) -> **OpenRouter** -> **HuggingFace** seamlessly if any provider rate limits or goes offline.
3. **Strict Document Isolation**: Isolates vector similarity searches strictly to the current conversation session (`filter_file_ids`), preventing cross-session document leakage.
4. **Local Embeddings & Cross-Encoder Reranking**: Computes dense embeddings (`all-MiniLM-L6-v2`) and reranks search hits (`cross-encoder/ms-marco-MiniLM-L-6-v2`) locally on CPU for high precision.
5. **Formal Grounded Synthesis**: Generates professional, unified, structured notes without artificial section headings, complete with real-time UI source panel tracking.

---

## 📐 System Architecture

```mermaid
graph TD
    User([End User]) -->|HTTPS / JWT| FE[Next.js 15 Frontend on Vercel]
    FE -->|REST API| BE[FastAPI Backend on AWS App Runner / ECS]

    subgraph langgraph_workflow ["LangGraph Multi-Agent State Machine"]
        BE -->|StateGraph| Supervisor[supervisor_node]
        Supervisor -->|Route: parallel| ParallelNode[Parallel Branching]
        
        ParallelNode -->|Concurrent Task| SearchNode[search_node]
        ParallelNode -->|Concurrent Task| SummaryNode[summary_node]
        
        SearchNode -->|Vector RPC| VectorSvc[Search Service]
        VectorSvc -->|Local Embeddings| MiniLM[SentenceTransformers]
        VectorSvc -->|Rerank Hits| CrossEncoder[CrossEncoder Reranker]
        
        SearchNode --> GroundedNode[grounded_generation_node]
        SummaryNode --> GroundedNode
    end

    subgraph failover_engine ["Multi-Provider LLM Failover Engine"]
        GroundedNode --> FailoverPool{LLM Service Pool}
        FailoverPool -->|Primary (~500 tps)| Groq[Groq Llama 3.1 8B]
        FailoverPool -->|Fallback 1| OpenRouter[OpenRouter Free Tier]
        FailoverPool -->|Fallback 2| HuggingFace[HuggingFace Router]
    end

    subgraph databases ["Storage & Caching"]
        VectorSvc -->|pgvector Cosine Search| Supabase[(Supabase PostgreSQL)]
        BE -->|Session Memory & Cache| Redis[(Upstash Redis Stack)]
    end
```

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS | High-fidelity console dashboard, dynamic document quick prompts, and live routing telemetry. |
| **Backend** | FastAPI, Pydantic v2, Uvicorn, Docker | High-performance ASGI async gateway and containerized execution server. |
| **Orchestration** | LangGraph, LangChain | StateGraph multi-agent routing, parallel node branching, and tool decorators. |
| **Vector DB** | Supabase (PostgreSQL + `pgvector`) | User authentication, session metadata, file metadata, and vector embeddings storage. |
| **Cache & Memory**| Upstash Redis Stack | Chat session memory, vector query caching, and rate limiting. |
| **LLM Failover** | Groq, OpenRouter, HuggingFace | Multi-provider fallback gateway with live model tracking in UI. |
| **Observability** | LangSmith & Langfuse | Distributed agent tracing, step execution logs, and latency monitoring. |

---

## 🚀 Quick Start (Local Setup)

### 1. Database & Prerequisites
Ensure Docker is installed, then launch Redis:
```bash
docker compose up -d
```

### 2. Backend Setup (FastAPI)
```bash
cd backend
python -m venv venv

# Activate venv
# Windows (CMD): venv\Scripts\activate
# Windows (PowerShell): .\venv\Scripts\Activate.ps1
# Linux/macOS: source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup (Next.js)
```bash
cd frontend
npm install
cp .env.example .env.local

# Start Next.js dev server
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 🌐 Production Deployment Guide (AWS + Vercel)

This application is designed to be deployed using **Vercel** for the frontend and **AWS App Runner / ECS** for the containerized backend.

- 📖 **[Full AWS + Vercel Deployment Manual](docs/aws_vercel_deployment.md)**
- 📐 **[Detailed Architecture Overview](docs/architecture_overview.md)**
- 🔌 **[API Endpoint Reference](docs/api_reference.md)**

---

## 🔑 Key Environment Variables (`backend/.env`)

```env
LLM_PROVIDER=llm
GROQ_API_KEY=gsk_your_groq_api_key
OPENROUTER_API_KEY=sk-or-v1-your_openrouter_key
GEMINI_API_KEY=your_gemini_key
SUPABASE_URL=https://your-supabase-project.supabase.co
SUPABASE_SERVICE_KEY=your-supabase-service-role-key
REDIS_URL=redis://:password@localhost:6379/0
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_your_langsmith_key
LANGCHAIN_PROJECT=agentic-ai
```

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for details.