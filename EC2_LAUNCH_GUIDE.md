# EC2 Launch Guide for Construction RAG

## 🚀 Quick Launch Steps

### 1. Launch EC2 Instance
```bash
Instance Type: t3.large
AMI: Ubuntu Server 22.04 LTS (ami-0c7217cdde317cfec)
Storage: 30 GB gp3
Key Pair: Use your existing key
```

### 2. Security Group Settings
```bash
# Create new security group: construction-rag-sg
Type            Protocol    Port Range    Source
SSH             TCP         22           Your IP/0.0.0.0/0
HTTP            TCP         80           0.0.0.0/0
HTTPS           TCP         443          0.0.0.0/0
Custom TCP      TCP         8000         0.0.0.0/0
Custom TCP      TCP         3000         0.0.0.0/0
```

### 3. Launch & Connect
```bash
# Launch instance and note the public IP
# Connect via SSH
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
```

### 4. Run Deployment Script
```bash
# Copy and run the deployment script
wget https://raw.githubusercontent.com/your-repo/construction-rag/main/deploy.sh
chmod +x deploy.sh
./deploy.sh
```

### 5. Upload Your Code
```bash
# From your local machine:
scp -i your-key.pem -r ./backend ubuntu@YOUR_EC2_IP:/home/ubuntu/construction-rag/
scp -i your-key.pem -r ./frontend ubuntu@YOUR_EC2_IP:/home/ubuntu/construction-rag/
scp -i your-key.pem -r ./drawings ubuntu@YOUR_EC2_IP:/home/ubuntu/construction-rag/
```

### 6. Configure Environment
```bash
# On EC2 instance:
cd /home/ubuntu/construction-rag
cp .env.template .env
nano .env  # Add your API keys
```

### 7. Start Services
```bash
./start.sh
```

## 💰 Cost Management

### During Evaluation (3 days):
- **Running cost**: ~$6 total
- **Monitor**: Check AWS billing dashboard daily

### After Evaluation:
```bash
# Stop instance (keeps data, minimal storage cost)
aws ec2 stop-instances --instance-ids YOUR_INSTANCE_ID

# Or terminate completely (deletes everything)
aws ec2 terminate-instances --instance-ids YOUR_INSTANCE_ID
```

## 🔧 Troubleshooting

### Check Service Status:
```bash
docker compose ps
docker compose logs backend
docker compose logs frontend
```

### Restart Services:
```bash
./stop.sh
./start.sh
```

### Check System Resources:
```bash
free -h          # Memory usage
df -h            # Disk usage
docker stats     # Container resource usage
```

## 🌐 Access URLs

Once deployed:
- **Frontend**: `http://YOUR_EC2_IP`
- **Backend API**: `http://YOUR_EC2_IP/api`
- **API Docs**: `http://YOUR_EC2_IP/api/docs`
- **Health Check**: `http://YOUR_EC2_IP/health`

## 📊 Expected Resource Usage (t3.large)

```
Service         CPU    Memory
PostgreSQL      5%     512MB
Letta          10%     1.5GB
Backend        15%     512MB
Frontend       10%     512MB
Nginx           2%     64MB
System         10%     1GB
----------------------------
Total          52%     4.1GB
Available      48%     3.9GB (comfortable buffer)
```

## ✅ Pre-Launch Checklist

- [ ] EC2 key pair ready
- [ ] Security group configured
- [ ] API keys available (OpenAI, Pinecone)
- [ ] Code ready to upload
- [ ] Domain purchased (optional)
- [ ] Billing alerts set up
