# Google Meet Sentiment Analysis Bot

An enterprise-grade Chrome extension that automatically joins Google Meet sessions, records audio, performs real-time sentiment analysis, and sends email notifications when sentiment turns negative.

## 🏗️ Architecture

```
├── chrome-extension/          # Chrome extension frontend
├── backend/                   # Python backend services
├── selenium-bot/             # Meeting automation
├── config/                   # Configuration files
├── docs/                     # Documentation
├── scripts/                  # Deployment scripts
└── tests/                    # Test suites
```

## 🚀 Features

- **Automated Meeting Join**: Selenium-based bot that joins Google Meet without detection
- **Real-time Audio Processing**: Continuous audio recording and transcription
- **Sentiment Analysis**: ML-powered sentiment detection with configurable thresholds
- **Email Notifications**: Automated alerts when sentiment turns negative
- **Enterprise Security**: Secure API endpoints, encrypted storage, audit logging
- **Scalable Architecture**: Microservices design for enterprise deployment

## 🛠️ Technology Stack

- **Frontend**: HTML5, CSS3, jQuery, Chrome Extension APIs
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Redis
- **Automation**: Selenium WebDriver with undetected-chromedriver
- **ML/AI**: OpenAI Whisper, TextBlob/VADER sentiment analysis
- **Infrastructure**: Docker, PostgreSQL, Nginx

## 📋 Prerequisites

- Chrome Browser (v100+)
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL
- Redis

## 🚀 Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository>
   cd google-meet-sentiment-bot
   ./scripts/setup.sh
   ```

2. **Configure Environment**
   ```bash
   cp config/.env.example config/.env
   # Edit config/.env with your settings
   ```

3. **Install Dependencies**
   ```bash
   ./scripts/install.sh
   ```

4. **Start Services**
   ```bash
   docker-compose up -d
   ```

5. **Load Chrome Extension**
   - Open Chrome → Extensions → Developer mode
   - Load unpacked → Select `chrome-extension/` folder

## 📖 Documentation

- [Installation Guide](docs/installation.md)
- [Configuration Reference](docs/configuration.md)
- [API Documentation](docs/api.md)
- [Security Guidelines](docs/security.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🔒 Security & Compliance

- End-to-end encryption for audio data
- GDPR-compliant data handling
- Secure credential management
- Audit logging and monitoring
- Rate limiting and DDoS protection

## 📧 Support

For enterprise support and deployment assistance, contact: support@company.com

## 📄 License

Proprietary - Enterprise License