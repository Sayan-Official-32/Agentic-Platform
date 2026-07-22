# Production Deployment Manual: AWS App Runner / ECS + Vercel

This document provides complete, step-by-step instructions to deploy the Agentic AI Platform to production using **AWS** for the FastAPI backend and **Vercel** for the Next.js frontend.

---

## Architecture Overview

```
                          ┌─────────────────────────────┐
                          │   Vercel Edge Network       │
                          │   (Next.js 15 Frontend)     │
                          └──────────────┬──────────────┘
                                         │ HTTPS API Calls
                                         ▼
                          ┌─────────────────────────────┐
                          │    AWS App Runner / ECS     │
                          │   (FastAPI Dockerized)      │
                          └──────┬───────────────┬──────┘
                                 │               │
                                 ▼               ▼
                       ┌────────────────┐ ┌──────────────┐
                       │ Supabase DB    │ │ Upstash Redis│
                       │ (pgvector RAG) │ │ (Cache/Mem)  │
                       └────────────────┘ └──────────────┘
```

---

## Part 1: Deploying Backend to AWS App Runner (Recommended)

AWS App Runner provides fully managed container execution with auto-scaling, HTTPS, and automatic health checks.

### Step 1.1: Push Docker Image to AWS ECR (Elastic Container Registry)

1. Open AWS Console and navigate to **ECR**.
2. Click **Create repository**:
   - Name: `agentic-ai-backend`
   - Tag immutability: Enabled
3. Authenticate Docker CLI to your ECR registry (run in terminal):
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
   ```
4. Build and tag your backend image:
   ```bash
   cd backend
   docker build -t agentic-ai-backend .
   docker tag agentic-ai-backend:latest <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/agentic-ai-backend:latest
   ```
5. Push image to AWS ECR:
   ```bash
   docker push <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/agentic-ai-backend:latest
   ```

### Step 1.2: Create AWS App Runner Service

1. Navigate to **AWS App Runner** in the console.
2. Click **Create service**.
3. Under **Source**:
   - Repository type: **Container registry**
   - Provider: **Amazon ECR**
   - Container image URI: Choose `<YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/agentic-ai-backend:latest`
   - Deployment trigger: **Automatic** (re-deploys when you push new ECR images).
4. Under **Configure service**:
   - Service name: `agentic-ai-backend`
   - CPU: `1 vCPU`
   - Memory: `2 GB`
   - Port: `8000`
5. Under **Environment variables**, add the production secrets:
   ```env
   APP_ENV=production
   LLM_PROVIDER=llm
   GROQ_API_KEY=gsk_your_groq_key
   OPENROUTER_API_KEY=sk-or-v1-your_openrouter_key
   GEMINI_API_KEY=your_gemini_key
   SUPABASE_URL=https://xzohxeygojwicycvcxld.supabase.co
   SUPABASE_SERVICE_KEY=your_supabase_service_role_key
   SUPABASE_STORAGE_BUCKET=user-documents
   REDIS_URL=rediss://default:your-password@your-endpoint.upstash.io:6379
   AUTH_SECRET_KEY=your_strong_jwt_secret_key
   BACKEND_CORS_ORIGINS=https://your-app-name.vercel.app
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=lsv2_pt_your_key
   LANGCHAIN_PROJECT=agentic-ai
   ```
6. Click **Create & Deploy**.
7. Copy your assigned AWS App Runner URL (e.g. `https://xyz123.us-east-1.awsapprunner.com`).

---

## Part 2: Deploying Frontend to Vercel

### Step 2.1: Import Project to Vercel

1. Log in to **[Vercel](https://vercel.com/)**.
2. Click **Add New** -> **Project**.
3. Import your GitHub repository.
4. Set **Root Directory**: `frontend`
5. Set **Framework Preset**: `Next.js`

### Step 2.2: Add Environment Variables

Add the following environment variable in the Vercel project settings:
* **Key**: `NEXT_PUBLIC_BACKEND_URL`
* **Value**: `https://xyz123.us-east-1.awsapprunner.com` (Your AWS App Runner URL from Part 1).

### Step 2.3: Deploy & Domain Setup

1. Click **Deploy**. Vercel will build and publish your Next.js frontend to `https://your-project.vercel.app`.
2. Copy your Vercel deployment URL.

---

## Part 3: Production Security & CORS Linkage

1. Return to your **AWS App Runner Service** settings.
2. Update the environment variable `BACKEND_CORS_ORIGINS`:
   `https://your-project.vercel.app`
3. Save changes. AWS App Runner will perform a zero-downtime rolling update.

Your application is now fully deployed in production!
