# Deployment Guide - Google Meet Sentiment Analysis Bot

This guide provides comprehensive instructions for deploying the Google Meet Sentiment Analysis Bot in enterprise environments.

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [System Requirements](#system-requirements)
3. [Installation Methods](#installation-methods)
4. [Configuration](#configuration)
5. [Security Considerations](#security-considerations)
6. [Production Deployment](#production-deployment)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)
9. [Support](#support)

## 🚀 Quick Start

### Automated Setup

```bash
# Clone the repository
git clone <repository-url>
cd google-meet-sentiment-bot

# Run automated setup for development
./scripts/setup.sh --dev

# Or for production
./scripts/setup.sh --prod
```

### Manual Setup

```bash
# 1. Setup environment
cp config/.env.example config/.env
# Edit config/.env with your settings

# 2. Start with Docker Compose
docker-compose up -d

# 3. Load Chrome extension
# Open Chrome → Extensions → Developer mode → Load unpacked → chrome-extension/
```

## 📋 System Requirements

### Minimum Requirements

- **OS**: Linux (Ubuntu 20.04+, RHEL 8+), macOS 11+, Windows 10+
- **CPU**: 4 cores, 2.5 GHz
- **RAM**: 8 GB (16 GB recommended)
- **Storage**: 50 GB available space
- **Network**: Stable internet connection (10 Mbps+)

### Software Prerequisites

- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+
- **Node.js**: 16+
- **Chrome Browser**: 100+

### Production Requirements

- **CPU**: 8+ cores
- **RAM**: 32+ GB
- **Storage**: 500+ GB SSD
- **Network**: Dedicated network, firewall configured
- **SSL Certificate**: For HTTPS deployment

## 🔧 Installation Methods

### Method 1: Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Method 2: Kubernetes

```yaml
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n meet-sentiment-bot

# Access services
kubectl port-forward svc/backend 8000:8000
```

### Method 3: Manual Installation

```bash
# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Setup databases
sudo systemctl start postgresql redis

# Run application
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## ⚙️ Configuration

### Environment Variables

Copy `config/.env.example` to `config/.env` and configure:

```bash
# Core Configuration
ENVIRONMENT=production
SECRET_KEY=your-64-character-secret-key
DATABASE_URL=postgresql://user:pass@localhost:5432/meet_sentiment_bot
REDIS_URL=redis://localhost:6379/0

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your-email@company.com
MAIL_PASSWORD=your-app-password
MAIL_FROM=alerts@company.com

# Security
CORS_ORIGINS=https://yourdomain.com,chrome-extension://your-extension-id
TRUSTED_HOSTS=yourdomain.com,api.yourdomain.com

# Sentiment Analysis
SENTIMENT_MODEL=vader
SENTIMENT_THRESHOLD_NEGATIVE=-0.1
WHISPER_MODEL=base
```

### Chrome Extension Configuration

1. **Load Extension**:
   - Open Chrome → `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `chrome-extension/` folder

2. **Configure Extension**:
   - Click extension icon
   - Set Backend URL to your API endpoint
   - Configure email alerts
   - Set sentiment thresholds

### Database Configuration

```sql
-- Create database
CREATE DATABASE meet_sentiment_bot;
CREATE USER meet_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE meet_sentiment_bot TO meet_user;

-- Run migrations
python -m alembic upgrade head
```

## 🔒 Security Considerations

### Network Security

```bash
# Configure firewall (Ubuntu/Debian)
sudo ufw allow 22/tcp          # SSH
sudo ufw allow 80/tcp          # HTTP
sudo ufw allow 443/tcp         # HTTPS
sudo ufw allow 8000/tcp        # API (internal only)
sudo ufw enable

# Use reverse proxy (Nginx)
sudo apt install nginx
sudo systemctl enable nginx
```

### SSL/TLS Configuration

```nginx
# /etc/nginx/sites-available/meet-sentiment-bot
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### API Security

- Use strong secret keys (64+ characters)
- Enable CORS only for required origins
- Implement rate limiting
- Use HTTPS in production
- Regularly update dependencies

### Data Protection

- Encrypt sensitive data at rest
- Use secure password policies
- Implement proper access controls
- Regular security audits
- GDPR compliance for EU operations

## 🏭 Production Deployment

### AWS Deployment

```bash
# 1. Setup ECS Cluster
aws ecs create-cluster --cluster-name meet-sentiment-bot

# 2. Deploy with Terraform
cd terraform/aws
terraform init
terraform plan
terraform apply

# 3. Configure Load Balancer
aws elbv2 create-load-balancer \
    --name meet-sentiment-bot-lb \
    --subnets subnet-12345 subnet-67890
```

### Google Cloud Deployment

```bash
# 1. Setup GKE Cluster
gcloud container clusters create meet-sentiment-bot \
    --num-nodes=3 \
    --zone=us-central1-a

# 2. Deploy to Kubernetes
kubectl apply -f k8s/

# 3. Configure Ingress
kubectl apply -f k8s/ingress.yaml
```

### Azure Deployment

```bash
# 1. Create Container Instance
az container create \
    --resource-group myResourceGroup \
    --name meet-sentiment-bot \
    --image meet-sentiment-bot:latest

# 2. Setup Application Gateway
az network application-gateway create \
    --name meet-sentiment-bot-gateway \
    --resource-group myResourceGroup
```

### High Availability Setup

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  backend:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  postgres:
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.role == manager

  redis:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
```

## 📊 Monitoring & Maintenance

### Health Checks

```bash
# API Health
curl http://localhost:8000/health

# Database Health
docker-compose exec postgres pg_isready

# Redis Health
docker-compose exec redis redis-cli ping

# Full System Health
curl http://localhost:8000/health/detailed
```

### Monitoring Stack

1. **Prometheus**: Metrics collection
   - Access: `http://localhost:9090`
   - Scrapes application metrics

2. **Grafana**: Visualization
   - Access: `http://localhost:3000`
   - Username: `admin`, Password: `admin123`

3. **ELK Stack**: Log aggregation
   - Kibana: `http://localhost:5601`
   - Elasticsearch: `http://localhost:9200`

### Backup Strategy

```bash
# Automated Database Backup
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL Backup
pg_dump -h localhost -U postgres meet_sentiment_bot > \
    $BACKUP_DIR/db_backup_$DATE.sql

# Redis Backup
redis-cli --rdb $BACKUP_DIR/redis_backup_$DATE.rdb

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +30 -delete
```

### Log Rotation

```bash
# /etc/logrotate.d/meet-sentiment-bot
/var/log/meet-sentiment-bot/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

### Update Procedure

```bash
# 1. Backup current deployment
docker-compose exec postgres pg_dump -U postgres meet_sentiment_bot > backup.sql

# 2. Pull latest images
docker-compose pull

# 3. Update with zero downtime
docker-compose up -d --no-deps backend

# 4. Run migrations if needed
docker-compose exec backend python -m alembic upgrade head

# 5. Verify deployment
curl http://localhost:8000/health
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Extension Not Loading

```bash
# Check extension manifest
cat chrome-extension/manifest.json

# Verify permissions
# Chrome → Extensions → Details → Permissions

# Check console errors
# Chrome → Developer Tools → Console
```

#### 2. Backend Connection Issues

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs backend

# Test connection
curl -v http://localhost:8000/health

# Check firewall
sudo ufw status
```

#### 3. Database Connection Failed

```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready

# Verify credentials
docker-compose exec postgres psql -U postgres -d meet_sentiment_bot -c "\dt"

# Check connection string
echo $DATABASE_URL
```

#### 4. Selenium Bot Issues

```bash
# Check Chrome installation
google-chrome --version

# Verify Selenium Grid
curl http://localhost:4444/wd/hub/status

# Check bot logs
docker-compose logs chrome-node
```

#### 5. Audio Processing Errors

```bash
# Check FFmpeg installation
ffmpeg -version

# Verify Whisper model
python -c "import whisper; print(whisper.available_models())"

# Test audio processing
curl -X POST http://localhost:8000/api/v1/audio/test
```

### Performance Optimization

#### Database Optimization

```sql
-- Create indexes for better performance
CREATE INDEX idx_sessions_created_at ON sessions(created_at);
CREATE INDEX idx_sentiment_results_session_id ON sentiment_results(session_id);
CREATE INDEX idx_sentiment_results_timestamp ON sentiment_results(timestamp);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM sessions WHERE created_at > NOW() - INTERVAL '1 day';
```

#### Redis Optimization

```bash
# Configure Redis memory policy
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Monitor Redis performance
redis-cli INFO memory
redis-cli MONITOR
```

#### Application Optimization

```python
# Use connection pooling
# Configure worker processes
# Enable caching
# Optimize database queries
# Use async/await properly
```

### Debugging Steps

1. **Check System Resources**:
   ```bash
   # CPU and Memory
   htop
   
   # Disk Space
   df -h
   
   # Network
   netstat -tulpn
   ```

2. **Verify Services**:
   ```bash
   # All services status
   docker-compose ps
   
   # Individual service logs
   docker-compose logs -f [service-name]
   ```

3. **Test Components**:
   ```bash
   # API endpoints
   curl http://localhost:8000/health
   
   # Database connection
   docker-compose exec postgres psql -U postgres -c "SELECT 1"
   
   # Redis connection
   docker-compose exec redis redis-cli ping
   ```

## 📞 Support

### Enterprise Support

- **Email**: support@yourcompany.com
- **Documentation**: https://docs.yourcompany.com/meet-sentiment-bot
- **Status Page**: https://status.yourcompany.com
- **Support Portal**: https://support.yourcompany.com

### Community Support

- **GitHub Issues**: https://github.com/yourorg/meet-sentiment-bot/issues
- **Discussions**: https://github.com/yourorg/meet-sentiment-bot/discussions
- **Wiki**: https://github.com/yourorg/meet-sentiment-bot/wiki

### Professional Services

- **Implementation Consulting**: Available for enterprise customers
- **Custom Development**: Tailored solutions for specific requirements
- **Training & Workshops**: Team training and best practices
- **24/7 Support**: Premium support packages available

### Service Level Agreements (SLA)

- **Uptime**: 99.9% guaranteed uptime
- **Response Time**: 
  - Critical: 1 hour
  - High: 4 hours
  - Medium: 24 hours
  - Low: 72 hours
- **Resolution Time**: Based on severity and complexity

---

## 📄 Additional Resources

- [Installation Guide](installation.md)
- [Configuration Reference](configuration.md)
- [API Documentation](api.md)
- [Security Guidelines](security.md)
- [Troubleshooting Guide](troubleshooting.md)
- [Development Guide](development.md)

## 📋 Deployment Checklist

### Pre-Deployment

- [ ] System requirements verified
- [ ] Dependencies installed
- [ ] Configuration files updated
- [ ] SSL certificates obtained
- [ ] Security review completed
- [ ] Backup strategy implemented

### Deployment

- [ ] Services deployed successfully
- [ ] Health checks passing
- [ ] Database migrations completed
- [ ] Chrome extension loaded
- [ ] Email notifications configured
- [ ] Monitoring enabled

### Post-Deployment

- [ ] System performance verified
- [ ] End-to-end testing completed
- [ ] Documentation updated
- [ ] Team training conducted
- [ ] Support contacts established
- [ ] Maintenance schedule defined

---

For additional support or questions, please contact our enterprise support team.