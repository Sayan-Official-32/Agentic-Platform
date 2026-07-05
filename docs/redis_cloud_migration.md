# Migrating Redis from Local Docker to AWS Cloud

This guide outlines how to shift your local Docker Redis setup into the cloud. You have three primary options depending on your budget, network complexity, and security requirements.

---

## Migration Options Comparison

| Option | Easiest to Set Up | Cost | Publicly Reachable? | Security |
| :--- | :--- | :--- | :--- | :--- |
| **Option 1: Upstash Serverless (Hosted on AWS)** | ⭐⭐⭐⭐⭐ (5/5) | **Free** (Up to 10k req/day, then pay-per-use) | Yes (via SSL `rediss://`) | High (Token Auth + TLS) |
| **Option 2: AWS EC2 + Docker (Lift & Shift)** | ⭐⭐⭐ (3/5) | **Free Tier** (t2.micro/t3.micro free for 12 months) | Optional (Can restrict via Security Groups) | Medium-High (AWS Firewalls) |
| **Option 3: AWS ElastiCache (Cloud Native)** | ⭐⭐ (2/5) | **Paid** ($\approx \$15\text{/month}$ minimum) | No (VPC Restricted) | Maximum (VPC isolated) |

---

## Option 1: Upstash Serverless Redis (Recommended & Easiest)
Upstash is a serverless Redis provider that hosts databases directly on AWS infrastructure. It is the easiest option because it does not require complex AWS VPC configuration.

### Setup Steps:
1. Log in to the [Upstash Console](https://console.upstash.com).
2. Click **Create Database**.
3. Set a name (e.g., `agentic-redis`) and select **AWS** as the provider.
4. Select the region closest to your backend deployment (e.g., `us-east-1` or `eu-west-1`).
5. Enable **TLS** (Encrypted connection).
6. Copy the **Redis URL** from the Node.js or Python settings tab. It will look like:
   ```env
   REDIS_URL=rediss://default:your_password@your-endpoint.upstash.io:6379/0
   ```
   *(Note the `rediss://` protocol indicating SSL encryption)*
7. Set this as the `REDIS_URL` in your AWS App Runner or ECS environment variables.

---

## Option 2: AWS EC2 running Redis via Docker (Free Tier Lift-and-Shift)
If you want to keep everything within your own AWS account without paying for ElastiCache, you can run your existing Docker setup on a free-tier EC2 instance.

### Setup Steps:
1. **Launch an EC2 Instance**:
   * Go to **EC2 Console** -> **Launch Instance**.
   * Name: `redis-host`.
   * Amazon Machine Image (AMI): **Amazon Linux 2023** or **Ubuntu**.
   * Instance type: `t2.micro` or `t3.micro` (Free Tier eligible).
   * Key pair: Create or select a key pair to SSH into the instance.
2. **Configure Security Group (Firewall)**:
   * Create a new security group.
   * Add **SSH (Port 22)**: Restrict to your IP.
   * Add **Custom TCP (Port 6379)**: Restrict source to your **AWS App Runner IP / ECS Service Security Group** to ensure public access is blocked.
3. **Install Docker on the Instance**:
   Connect to your EC2 instance via SSH (replace `your-key.pem` and `your-ec2-public-ip` with your actual key name and public IP. Note: if you are already inside the EC2 terminal, e.g. showing `ubuntu@ip-...`, you do not need to run SSH inside it):
   ```bash
   ssh -i your-key.pem ec2-user@your-ec2-public-ip
   ```
   
   Identify your OS and run the appropriate commands:

   * **For Ubuntu (packages use `apt`):**
     ```bash
     sudo apt update -y
     sudo apt install -y docker.io
     sudo systemctl start docker
     sudo systemctl enable docker
     sudo usermod -aG docker ubuntu
     newgrp docker # Apply group membership without logout
     ```

   * **For Amazon Linux 2023 (packages use `dnf`):**
     ```bash
     sudo dnf update -y
     sudo dnf install -y docker
     sudo systemctl start docker
     sudo systemctl enable docker
     sudo usermod -aG docker ec2-user
     newgrp docker # Apply group membership without logout
     ```

4. **Run the Redis Container**:
   Run Redis with authentication enabled matching your local password:
   ```bash
   docker run -d \
     --name agentic-redis \
     -p 6379:6379 \
     -v redis_data:/data \
     --restart unless-stopped \
     redis:alpine redis-server --requirepass redis_password
   ```
5. **Get Connection String**:
   Your production environment variable on your backend will be:
   ```env
   REDIS_URL=redis://:redis_password@your-ec2-private-ip:6379/0
   ```
   *(If both backend and EC2 are in the same VPC, use the Private IP. Otherwise, use the Public IP).*

---

## Option 3: AWS ElastiCache for Redis (Managed Enterprise Way)
AWS ElastiCache is AWS's native managed Redis service. Because it is VPC-isolated, you must configure network peering or connectors to allow your backend to reach it.

### Setup Steps:
1. **Create ElastiCache Cluster**:
   * Open the **Amazon ElastiCache Console**.
   * Under **Redis OSS**, click **Create Redis cluster**.
   * Choose **Configure and create a new cluster**.
   * Deployment option: **Serverless** or **Self-designed** (For self-designed, select `cache.t4g.micro` to keep costs low).
   * Set **Multi-AZ** to Disabled (to reduce costs).
   * Set **Encryption in transit (TLS)** and **Encryption at rest** to Enabled.
   * Under **Access control**, select **Redis AUTH** and enter a password.
2. **Configure Networking (VPC & Subnets)**:
   * Select your VPC.
   * Create a Subnet Group representing the private subnets where your Redis cluster will reside.
3. **Configure Security Group**:
   * Create a Security Group for ElastiCache.
   * Add an **Inbound Rule** allowing Custom TCP on Port `6379` from the Security Group of your FastAPI backend service (ECS or App Runner VPC Connector).
4. **Connect your Backend via AWS VPC Connector**:
   ElastiCache has no public IP addresses. To access it:
   * **If using AWS App Runner**: In your App Runner Service, enable **Outgoing Network Traffic** and choose **Custom VPC**. Create a VPC Connector linking the private subnets of the ElastiCache VPC.
   * **If using ECS Fargate**: Launch your ECS Tasks in the *same VPC* as ElastiCache, using the same subnets.
5. **Get Connection String**:
   Once ElastiCache boots, copy the **Primary Endpoint** URL.
   ```env
   REDIS_URL=rediss://default:your_redis_auth_password@your-elasticache-endpoint.amazonaws.com:6379/0
   ```
