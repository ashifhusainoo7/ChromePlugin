# Quick Installation Guide

## 🚀 Two-Step Installation Process

### Step 1: Install Dependencies
Use the `install.sh` script to install all system dependencies:

```bash
# Clone the repository
git clone <repository-url>
cd google-meet-sentiment-bot

# Run the installation script
./scripts/install.sh
```

This script will install:
- Python 3.11+
- Node.js 16+
- Docker & Docker Compose
- Google Chrome & ChromeDriver
- PostgreSQL & Redis
- FFmpeg and other system dependencies
- Python virtual environment and dependencies

### Step 2: Setup and Start Services
Use the `setup.sh` script to configure and start the application:

```bash
# For development environment
./scripts/setup.sh --dev

# For production environment
./scripts/setup.sh --prod

# Just to start services (after initial setup)
./scripts/setup.sh --start
```

## 📋 Script Overview

### `./scripts/install.sh`
- **Purpose**: Installs all system dependencies and prerequisites
- **Run once**: Only needs to be run once per system
- **Cross-platform**: Works on Ubuntu, CentOS, macOS
- **What it does**:
  - Detects your operating system
  - Installs Python 3.11, Node.js, Docker
  - Installs Chrome and ChromeDriver
  - Sets up databases (PostgreSQL, Redis)
  - Creates Python virtual environment
  - Installs Python dependencies

### `./scripts/setup.sh`
- **Purpose**: Configures and starts the application services
- **Run multiple times**: Can be run whenever you want to start/restart
- **What it does**:
  - Creates configuration files
  - Sets up Chrome extension
  - Initializes database
  - Starts Docker services
  - Runs health checks
  - Optionally runs tests

## 🔧 Manual Installation (Alternative)

If you prefer to install manually or the scripts don't work on your system:

### 1. Install Prerequisites
```bash
# Python 3.11+
sudo apt install python3.11 python3.11-venv python3.11-dev

# Node.js 16+
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt-get install -y nodejs

# Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Google Chrome
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt update && sudo apt install google-chrome-stable

# Other dependencies
sudo apt install ffmpeg postgresql redis-server
```

### 2. Setup Application
```bash
# Create Python environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
cd backend
pip install -r requirements.txt
cd ..

# Setup configuration
cp config/.env.example config/.env
# Edit config/.env with your settings

# Start services
docker-compose up -d
```

### 3. Load Chrome Extension
1. Open Chrome
2. Go to `chrome://extensions/`
3. Enable "Developer mode"
4. Click "Load unpacked"
5. Select the `chrome-extension/` folder

## 🏗️ Directory Structure After Installation

```
google-meet-sentiment-bot/
├── chrome-extension/          # Chrome extension files
│   ├── manifest.json         # Extension manifest
│   ├── popup/               # Popup UI
│   ├── background/          # Background scripts
│   ├── content/            # Content scripts
│   └── assets/             # CSS, JS, images
├── backend/                 # Python FastAPI backend
│   ├── app/                # Application code
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile         # Docker configuration
├── selenium-bot/           # Selenium automation
│   └── src/               # Bot source code
├── config/                 # Configuration files
│   ├── .env               # Environment variables
│   └── .env.example       # Template
├── scripts/               # Installation scripts
│   ├── install.sh         # Dependencies installer
│   └── setup.sh          # Application setup
├── docs/                  # Documentation
├── venv/                  # Python virtual environment
├── logs/                  # Application logs
├── uploads/               # File uploads
├── backups/               # Database backups
└── docker-compose.yml     # Docker services
```

## ✅ Verification Steps

After installation, verify everything is working:

```bash
# Check Python
python3.11 --version

# Check Node.js
node --version

# Check Docker
docker --version
docker-compose --version

# Check Chrome
google-chrome --version

# Check services
docker-compose ps

# Check API
curl http://localhost:8000/health
```

## 🆘 Troubleshooting

### Common Issues

**1. Permission denied for Docker**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

**2. Python 3.11 not found**
```bash
# Ubuntu/Debian
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11
```

**3. Chrome/ChromeDriver issues**
```bash
# Check versions match
google-chrome --version
chromedriver --version
```

**4. Port conflicts**
```bash
# Check what's using ports
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :5432
```

### Get Help

- Check logs: `docker-compose logs -f`
- Restart services: `docker-compose restart`
- Clean restart: `docker-compose down && docker-compose up -d`
- Check system resources: `htop` or `docker stats`

## 🎯 Next Steps

After successful installation:

1. **Configure**: Edit `config/.env` with your email settings and API keys
2. **Test**: Run `./scripts/setup.sh --test` to verify everything works
3. **Use**: Load the Chrome extension and join a Google Meet
4. **Monitor**: Access Grafana at http://localhost:3000 for monitoring
5. **Logs**: View logs at http://localhost:5601 (Kibana)

For detailed configuration and usage instructions, see the [main README.md](README.md) and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).