# Agentic AI Chat System - Production Deployment Plan (Vercel & AWS)

This document provides a step-by-step, enterprise-grade deployment plan for hosting the **Agentic AI Chat System** in production. 

* **Frontend**: Next.js 15 app deployed on **Vercel**.
* **Backend**: FastAPI app deployed on **AWS** (options for AWS App Runner or AWS ECS Fargate).
* **Databases & Cache**: Hosted on **Supabase Cloud** (PostgreSQL + pgvector + Object Storage) and **Upstash Redis** (Serverless Cache).

---

## 1. Prerequisites Checklist

Ensure you have created accounts and have active credentials for the following platforms:
1. **AWS Console Account**: With permissions to create App Runner services, ECS clusters, or ECR repositories.
2. **Vercel Account**: For deploying the Next.js frontend.
3. **Supabase Account**: For hosting the PostgreSQL database and file storage buckets.
4. **Upstash Account** (or Redis Enterprise Cloud): For serverless Redis.
5. **Hugging Face Account**: To generate an API token with serverless inference access.
6. **GitHub Repository**: Storing your current codebase (containing `/backend` and `/frontend`).

---

## 2. Databases & Storage Infrastructure Setup

### Step A: PostgreSQL + pgvector (Supabase Cloud)
1. **Create Project**: Log in to [Supabase](https://supabase.com) and create a new project. Choose a database region closest to your planned AWS backend region (e.g., `us-east-1` or `eu-west-1`).
2. **Execute Migrations**:
   * Navigate to the **SQL Editor** tab in your Supabase dashboard.
   * Open each migration file from `backend/supabase/migrations/` in order and run them:
     1. `001_extensions_users.sql` (Enables vector and UUID extensions, creates users table)
     2. `002_user_files.sql` (Creates user files metadata table)
     3. `003_document_chunks.sql` (Creates document chunks table with pgvector type)
     4. `004_conversation_sessions.sql` (Creates conversation sessions table)
     5. `005_similarity_rpc.sql` (Creates cosine similarity RPC search query)
     6. `006_conversation_messages.sql` (Creates conversation messages table)
3. **Retrieve Credentials**:
   * Navigate to **Project Settings** -> **API**.
   * Copy the **Project URL** (`SUPABASE_URL`) and the **Service Role JWT Key** (`SUPABASE_SERVICE_KEY`).
   > [!WARNING]
   > Never use the public `anon` key for the backend service. Only use the `service_role` key, as the backend needs write and delete access across all users' collections.

### Step B: Object Storage (Supabase Buckets)
1. Navigate to the **Storage** tab in your Supabase dashboard.
2. Click **New Bucket**.
3. Set the bucket name to `user-documents`.
4. Ensure the bucket is **Private** (recommended for data privacy) and click save.

### Step C: Serverless Cache (Upstash Redis)
1. Log in to [Upstash](https://upstash.com) and click **Create Database**.
2. Select a region matching your Supabase/AWS region to reduce cross-region latency.
3. Copy the **Redis URL** connection string (e.g., `rediss://default:your-password@your-endpoint.upstash.io:6379`).

---

## 3. Backend Deployment on AWS

Because the backend runs heavy Python packages (such as `torch`, `sentence-transformers` for local embeddings, and `cross-encoder` models for reranking), **AWS Lambda is not recommended** due to high execution startup times (cold starts) and size limit boundaries. 

Instead, use one of the containerized options below. A production-ready [Dockerfile](file:///c:/Users/ASUS/OneDrive/Documents/VSCODE/agentic-ai/backend/Dockerfile) has been added to `/backend` which pre-downloads the model weights during build-time to eliminate cold starts.

### Option A: AWS App Runner (Recommended - Simplest & Managed)
AWS App Runner is a fully managed service that takes a container image or a GitHub repository and builds/runs it automatically, handling load balancing, SSL, auto-scaling, and domain configuration.

1. **Configure Connection**:
   * Open the **AWS App Runner Console**.
   * Click **Create Service**.
   * Choose **Source code repository**, connect your GitHub account, and select your repository.
   * Set the branch to `main` and the deployment trigger to **Automatic** (CI/CD).
2. **Configure Build Settings**:
   * Choose **Configure all settings here**.
   * **Runtime**: Choose `Python 3` (or choose **Container image** if you build the container via ECR).
   * If using source code, configure the build commands:
     * **Build command**: `cd backend && pip install -r requirements.txt`
     * **Start command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8080`
     * **Port**: `8080` (or `8000` depending on port variable settings).
3. **Configure Environment Variables**:
   Add the following variables to the App Runner service:
   * `LLM_PROVIDER`: `huggingface`
   * `HUGGINGFACE_API_KEY`: `<your_huggingface_api_token>`
   * `REDIS_URL`: `rediss://default:password@endpoint:port`
   * `SUPABASE_URL`: `https://your-project.supabase.co`
   * `SUPABASE_SERVICE_KEY`: `<your_service_role_key>`
   * `SUPABASE_STORAGE_BUCKET`: `user-documents`
   * `BACKEND_CORS_ORIGINS`: `https://your-app.vercel.app` (You can update this after deploying to Vercel)
   * `AUTH_SECRET_KEY`: `<generate_a_long_random_jwt_signing_key>`
4. **Deploy**:
   * Click **Next**, review configurations, and select **Create & Deploy**.
   * Once deployed, App Runner provides a public URL (e.g. `https://xxxx.us-east-1.awsapprunner.com`). Save this URL.

---

### Option B: AWS ECS Fargate (Enterprise Standard)
If you require private VPC access, integration with AWS ElastiCache, or custom IAM role policies, deploy using ECS Fargate.

```
                  ┌──────────────────────────────┐
                  │      AWS ALB (HTTPS)         │
                  └──────────────┬───────────────┘
                                 │
                   ┌─────────────▼─────────────┐
                   │    ECS Fargate Service    │
                   │  (FastAPI Docker Container)│
                   └──────┬─────────────┬──────┘
                          │             │
  ┌───────────────────────▼──┐       ┌──▼─────────────────────────┐
  │   Supabase Cloud DB      │       │     Upstash Redis Cache    │
  │  (pgvector / PostgreSQL) │       │    (Session / cache)       │
  └──────────────────────────┘       └────────────────────────────┘
```

1. **Push Container to ECR**:
   * Create a repository in **Amazon ECR** named `agentic-backend`.
   * Log in to ECR using Docker CLI and build/tag/push the image:
     ```bash
     cd backend
     aws ecr get-login-password --region your-region | docker login --username AWS --password-stdin your-account-id.dkr.ecr.your-region.amazonaws.com
     docker build -t agentic-backend .
     docker tag agentic-backend:latest your-account-id.dkr.ecr.your-region.amazonaws.com/agentic-backend:latest
     docker push your-account-id.dkr.ecr.your-region.amazonaws.com/agentic-backend:latest
     ```
2. **Create ECS Task Definition**:
   * Go to **ECS Console** -> **Task Definitions** -> **Create New Task Definition**.
   * Family: `agentic-backend-task`.
   * Infrastructure: **AWS Fargate**.
   * Memory: `2 GB` (needed to run local model loading comfortably), CPU: `0.5 vCPU` or `1 vCPU`.
   * Container details:
     * Name: `api-container`.
     * Image URI: `your-account-id.dkr.ecr.your-region.amazonaws.com/agentic-backend:latest`.
     * Port mappings: Container port `8000`, Protocol `TCP`.
     * Add all backend environment variables listed under the App Runner section.
3. **Configure Load Balancer (ALB)**:
   * Create an **Application Load Balancer** in your VPC.
   * Add a HTTPS listener and map it to an target group routing traffic on port `8000` (HTTP).
4. **Create ECS Service**:
   * Under your ECS Cluster, click **Create Service**.
   * Launch Type: **Fargate**.
   * Task Definition: `agentic-backend-task`.
   * Service Name: `agentic-backend-service`.
   * Desired Tasks: `1` or `2` (for high availability).
   * Networking: Select subnets and ensure Security Groups allow inbound traffic from your ALB on port `8000`.
   * Load Balancing: Select the Application Load Balancer created above.

---

## 4. Frontend Deployment on Vercel

Vercel is optimized for Next.js out-of-the-box and provides automatic builds, edge functions routing, and preview environments.

1. **Import Project**:
   * Log in to your [Vercel Dashboard](https://vercel.com).
   * Click **Add New** -> **Project**.
   * Select your GitHub repository.
2. **Configure Framework & Directory**:
   * **Framework Preset**: `Next.js`.
   * **Root Directory**: Click Edit and select `frontend/`.
3. **Configure Environment Variables**:
   Add the following frontend environment variable:
   * `NEXT_PUBLIC_BACKEND_URL`: `https://your-backend-aws-url.com` (Your AWS App Runner URL or ALB Domain).
   > [!IMPORTANT]
   > Do not append a trailing slash to the backend URL. Keep it as `https://domain.com` or `https://api.domain.com`.
4. **Deploy**:
   * Click **Deploy**. Vercel will build the Next.js static pages, compile TypeScript, and serve the application.
   * Vercel will output a deployment link (e.g. `https://agentic-ai-frontend.vercel.app`).

---

## 5. Post-Deployment Alignments

### Align CORS Whitelist
FastAPI protects your endpoints by validating origin headers. You must update your backend settings to authorize requests coming from your production Vercel frontend.

1. Go to your **AWS App Runner** or **ECS Environment settings**.
2. Find the `BACKEND_CORS_ORIGINS` variable.
3. Update its value to include your production Vercel URL:
   ```env
   BACKEND_CORS_ORIGINS=https://agentic-ai-frontend.vercel.app,https://your-custom-domain.com
   ```
4. Restart/Redeploy the backend service on AWS to apply.

---

## 6. Verification and Testing

Verify the end-to-end integration of the production deployment:
1. **Health Check Probe**: Visit `https://your-backend-aws-url.com/health` in your browser. Ensure it responds with status `ok` and shows connection confirmations:
   ```json
   {
     "status": "ok",
     "redis_connected": true,
     "supabase_connected": true
   }
   ```
2. **Registration Flow**: Access your Vercel frontend URL, register a new account, and verify that the account is created successfully (records will appear in the `users` table on Supabase).
3. **Document Upload**:
   * Upload a sample PDF or CSV file in the sidebar.
   * Verify that the file status updates to `ready`.
   * Check your Supabase Storage dashboard to ensure the file is written inside the `user-documents` bucket.
   * Check the `document_chunks` table to verify vector embeddings are successfully generated and stored.
4. **Chat grounded routing**: Ask a question related to your uploaded file. Confirm that the supervisor routes to `parallel`, uses the `search` and `summary` agents, and returns a grounded response with source attributions.
