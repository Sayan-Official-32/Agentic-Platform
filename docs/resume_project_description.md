# Resume Project Descriptions - Agentic AI Chat System

This document contains pre-formatted project descriptions for the **Agentic AI Chat System** tailored to match your resume's style. You can copy and paste your preferred option directly into your CV.

---

### Option 1: Focus on Agentic Architecture & Machine Learning (Recommended)

**• Multi-Agent Cooperative RAG Platform** — [(Project Link)](https://github.com/Sayan-Official-32/Agentic-Platform) | **July 2026**
* Developed a production-ready Retrieval-Augmented Generation (RAG) platform using **FastAPI**, **Next.js 15**, **Supabase (PostgreSQL + pgvector)**, and **Redis**.
* Designed a dynamic multi-agent supervisor graph that routes natural language queries to specialized micro-agents for parallel search and summarization tasks.
* Integrated local SentenceTransformers and CrossEncoder reranking models to optimize search query context, delivering source-attributed answers with exact page numbers.
* Implemented caching and performance layers (Token-Bucket Rate Limiter, stateless JWT Auth, and Redis Cache), reducing average cache-hit latency to $\approx 45\text{ms}$.

---

### Option 2: Focus on Full-Stack Software Engineering & Scale

**• Agentic AI Chat System** — [(Project Link)](https://github.com/Sayan-Official-32/Agentic-Platform) | **July 2026**
* Architected a full-stack, multi-user AI chat application utilizing **Next.js 15 (TypeScript)** for the client dashboard and **FastAPI** for the backend API.
* Implemented secure document ingestion supporting 9 file formats, automated text chunking, and metadata mapping stored in **Supabase Storage** and pgvector.
* Optimized LLM token usage and service costs by implementing Redis memory caching for embedding vectors and redundant query responses.
* Created a real-time telemetry panel and integrated Langfuse observability to track downstream LLM API latencies, token counters, and active route decisions.

---

### Key Technical Keywords for your Resume:
* **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS, LocalStorage Session Guards.
* **Backend**: FastAPI, Pydantic, Uvicorn, Token-Bucket Rate Limiter, stateless JWT, bcrypt hashing.
* **Databases & Cache**: Supabase (PostgreSQL + pgvector), Supabase Storage, Redis Stack.
* **Machine Learning & AI**: SentenceTransformers (`all-MiniLM-L6-v2`), CrossEncoder Reranker (`ms-marco-MiniLM-L-6-v2`), Hugging Face Serverless Router API, Ollama Local Models, LangGraph execution.
