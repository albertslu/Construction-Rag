#!/bin/bash

# Construction RAG Deployment Script for EC2
# Optimized for t3.large (2 vCPU, 8GB RAM)
# Run this on a fresh Ubuntu 22.04 EC2 instance

set -e

echo "🚀 Starting Construction RAG Deployment..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker ubuntu
sudo systemctl enable docker
sudo systemctl start docker

# Install Node.js (for frontend builds)
echo "📦 Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Nginx
echo "🌐 Installing Nginx..."
sudo apt install -y nginx certbot python3-certbot-nginx

# Create project directory
echo "📁 Setting up project structure..."
mkdir -p /home/ubuntu/construction-rag
cd /home/ubuntu/construction-rag

# Create Docker Compose file
echo "🐳 Creating Docker Compose configuration..."
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: letta_db
      POSTGRES_USER: letta_user
      POSTGRES_PASSWORD: secure_letta_pass_123
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    shm_size: 256mb

  letta:
    image: letta/letta:latest
    environment:
      - LETTA_PG_DB=letta_db
      - LETTA_PG_USER=letta_user
      - LETTA_PG_PASSWORD=secure_letta_pass_123
      - LETTA_PG_HOST=postgres
      - LETTA_PG_PORT=5432
    depends_on:
      - postgres
    volumes:
      - letta_data:/root/.letta
    restart: unless-stopped
    expose:
      - "8283"

  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - PINECONE_INDEX_NAME=${PINECONE_INDEX_NAME:-construction-rag}
      - PINECONE_NAMESPACE=${PINECONE_NAMESPACE:-default}
      - LETTA_SERVER_URL=http://letta:8283
      - DATABASE_URL=postgresql://letta_user:secure_letta_pass_123@postgres:5432/letta_db
    depends_on:
      - postgres
      - letta
    volumes:
      - ./drawings:/app/drawings
    restart: unless-stopped
    expose:
      - "8000"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      - NEXT_PUBLIC_API_URL=/api
    restart: unless-stopped
    expose:
      - "3000"

volumes:
  postgres_data:
  letta_data:

networks:
  default:
    name: construction-rag-network
EOF

# Create backend Dockerfile
echo "🐳 Creating Backend Dockerfile..."
mkdir -p backend
cat > backend/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Create frontend Dockerfile
echo "🐳 Creating Frontend Dockerfile..."
mkdir -p frontend
cat > frontend/Dockerfile << 'EOF'
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["node", "server.js"]
EOF

# Create Nginx configuration
echo "🌐 Creating Nginx configuration..."
sudo tee /etc/nginx/sites-available/construction-rag << 'EOF'
server {
    listen 80;
    server_name _;
    
    client_max_body_size 50M;
    
    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Backend API
    location /api {
        rewrite ^/api/(.*) /$1 break;
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # Health check
    location /health {
        proxy_pass http://localhost:8000/healthz;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/construction-rag /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Create environment file template
echo "📝 Creating environment template..."
cat > .env.template << 'EOF'
# Copy this to .env and fill in your values
OPENAI_API_KEY=your_openai_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=construction-rag
PINECONE_NAMESPACE=default
EOF

# Create startup script
echo "🚀 Creating startup script..."
cat > start.sh << 'EOF'
#!/bin/bash
cd /home/ubuntu/construction-rag

echo "🚀 Starting Construction RAG services..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.template to .env and fill in your API keys"
    exit 1
fi

# Start services
docker compose up -d --build

echo "⏳ Waiting for services to start..."
sleep 30

# Check service status
docker compose ps

echo "✅ Services started!"
echo "🌐 Frontend: http://$(curl -s ifconfig.me)"
echo "🔧 Backend API: http://$(curl -s ifconfig.me)/api/docs"
echo "💾 To view logs: docker compose logs -f"
EOF

chmod +x start.sh

# Create stop script
cat > stop.sh << 'EOF'
#!/bin/bash
cd /home/ubuntu/construction-rag
echo "🛑 Stopping Construction RAG services..."
docker compose down
echo "✅ Services stopped!"
EOF

chmod +x stop.sh

# Test Nginx configuration
sudo nginx -t

# Start Nginx
sudo systemctl enable nginx
sudo systemctl start nginx

echo "✅ Deployment script completed!"
echo ""
echo "📋 Next steps:"
echo "1. Copy your backend/ and frontend/ code to /home/ubuntu/construction-rag/"
echo "2. Copy your drawings/ folder to /home/ubuntu/construction-rag/"
echo "3. Copy .env.template to .env and add your API keys"
echo "4. Run: ./start.sh"
echo ""
echo "🌐 Your app will be available at: http://$(curl -s ifconfig.me)"
echo "🔧 API docs will be at: http://$(curl -s ifconfig.me)/api/docs"
