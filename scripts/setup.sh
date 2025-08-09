#!/bin/bash

# Google Meet Sentiment Analysis Bot - Setup Script
# This script sets up the complete development and production environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root for security reasons"
        exit 1
    fi
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        OS="windows"
    else
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    log_info "Detected OS: $OS"
    
    # Check required commands
    local required_commands=("python3" "pip3" "node" "npm" "docker" "docker-compose")
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v $cmd &> /dev/null; then
            log_error "$cmd is required but not installed"
            exit 1
        fi
    done
    
    # Check Python version
    local python_version=$(python3 --version | cut -d' ' -f2)
    local required_python="3.11"
    
    if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
        log_error "Python 3.11+ is required. Current version: $python_version"
        exit 1
    fi
    
    # Check Node version
    local node_version=$(node --version | cut -d'v' -f2)
    local required_node="16.0.0"
    
    if ! node -e "process.exit(process.version.slice(1).split('.').map(Number).reduce((a,b,i)=>a+(b<<(8*(2-i))),0) >= 0x100000 ? 0 : 1)" 2>/dev/null; then
        log_error "Node.js 16+ is required. Current version: $node_version"
        exit 1
    fi
    
    # Check Docker
    if ! docker --version &> /dev/null; then
        log_error "Docker is required but not installed"
        exit 1
    fi
    
    if ! docker-compose --version &> /dev/null; then
        log_error "Docker Compose is required but not installed"
        exit 1
    fi
    
    log_success "All system requirements met"
}

# Setup environment configuration
setup_environment() {
    log_info "Setting up environment configuration..."
    
    if [[ ! -f "config/.env" ]]; then
        log_info "Creating environment configuration from template..."
        cp config/.env.example config/.env
        
        # Generate secure secret key
        local secret_key=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
        
        # Update config file with generated values
        if [[ "$OS" == "macos" ]]; then
            sed -i '' "s/your-secret-key-change-in-production-use-64-chars-minimum/$secret_key/g" config/.env
        else
            sed -i "s/your-secret-key-change-in-production-use-64-chars-minimum/$secret_key/g" config/.env
        fi
        
        log_warning "Please update config/.env with your specific configuration values"
        log_warning "Important: Update database URLs, email settings, and API keys"
    else
        log_info "Environment configuration already exists"
    fi
}

# Setup Python environment
setup_python() {
    log_info "Setting up Python environment..."
    
    # Create virtual environment if it doesn't exist
    if [[ ! -d "venv" ]]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip
    
    # Install Python dependencies
    log_info "Installing Python dependencies..."
    cd backend
    pip install -r requirements.txt
    cd ..
    
    log_success "Python environment setup complete"
}

# Setup Chrome extension
setup_chrome_extension() {
    log_info "Setting up Chrome extension..."
    
    cd chrome-extension
    
    # Download jQuery if not present
    if [[ ! -f "assets/js/jquery-3.7.1.min.js" ]]; then
        log_info "Downloading jQuery..."
        curl -o assets/js/jquery-3.7.1.min.js https://code.jquery.com/jquery-3.7.1.min.js
    fi
    
    # Create extension icons (placeholder)
    log_info "Creating extension icons..."
    mkdir -p assets/images
    
    # You would typically have actual icon files here
    # For now, we'll create placeholder text files
    for size in 16 32 48 128; do
        if [[ ! -f "assets/images/icon-${size}.png" ]]; then
            echo "Placeholder icon ${size}x${size}" > "assets/images/icon-${size}.png"
        fi
    done
    
    cd ..
    
    log_success "Chrome extension setup complete"
    log_info "To load the extension:"
    log_info "1. Open Chrome and go to chrome://extensions/"
    log_info "2. Enable 'Developer mode'"
    log_info "3. Click 'Load unpacked' and select the chrome-extension folder"
}

# Setup database
setup_database() {
    log_info "Setting up database..."
    
    # Start database services
    log_info "Starting database services..."
    docker-compose up -d postgres redis
    
    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    sleep 10
    
    # Run database migrations
    log_info "Running database migrations..."
    source venv/bin/activate
    cd backend
    
    # Create tables (you would use alembic in a real setup)
    python -c "
from app.core.database import engine, metadata
metadata.create_all(engine)
print('Database tables created successfully')
"
    
    cd ..
    
    log_success "Database setup complete"
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    
    case $OS in
        "linux")
            # Ubuntu/Debian
            if command -v apt-get &> /dev/null; then
                sudo apt-get update
                sudo apt-get install -y \
                    build-essential \
                    curl \
                    ffmpeg \
                    git \
                    libpq-dev \
                    wget \
                    chrome-browser \
                    postgresql-client \
                    redis-tools
            # RHEL/CentOS/Fedora
            elif command -v yum &> /dev/null; then
                sudo yum update -y
                sudo yum install -y \
                    gcc \
                    curl \
                    ffmpeg \
                    git \
                    postgresql-devel \
                    wget \
                    google-chrome-stable \
                    postgresql \
                    redis
            fi
            ;;
        "macos")
            # macOS with Homebrew
            if command -v brew &> /dev/null; then
                brew update
                brew install \
                    ffmpeg \
                    postgresql \
                    redis \
                    chromedriver
            else
                log_error "Homebrew is required on macOS. Please install it first."
                exit 1
            fi
            ;;
        "windows")
            log_warning "Manual installation of system dependencies required on Windows"
            log_info "Please install: Chrome, FFmpeg, PostgreSQL, Redis"
            ;;
    esac
    
    log_success "System dependencies installed"
}

# Setup development tools
setup_dev_tools() {
    log_info "Setting up development tools..."
    
    source venv/bin/activate
    cd backend
    
    # Install development dependencies
    pip install \
        pytest \
        pytest-asyncio \
        pytest-cov \
        black \
        isort \
        flake8 \
        mypy \
        pre-commit
    
    # Setup pre-commit hooks
    if [[ -f ".pre-commit-config.yaml" ]]; then
        pre-commit install
    fi
    
    cd ..
    
    log_success "Development tools setup complete"
}

# Start services
start_services() {
    log_info "Starting all services..."
    
    # Start with Docker Compose
    docker-compose up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to start..."
    sleep 30
    
    # Health check
    log_info "Performing health checks..."
    
    # Check backend
    if curl -f http://localhost:8000/health &> /dev/null; then
        log_success "Backend service is healthy"
    else
        log_warning "Backend service may not be ready yet"
    fi
    
    # Check database
    if docker-compose exec -T postgres pg_isready -U postgres &> /dev/null; then
        log_success "Database service is healthy"
    else
        log_warning "Database service may not be ready yet"
    fi
    
    log_success "Services started successfully"
}

# Run tests
run_tests() {
    log_info "Running tests..."
    
    source venv/bin/activate
    cd backend
    
    # Run Python tests
    python -m pytest tests/ -v --cov=app --cov-report=html
    
    cd ..
    
    log_success "Tests completed"
}

# Show usage information
show_usage() {
    echo "Google Meet Sentiment Analysis Bot - Setup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dev          Setup development environment"
    echo "  --prod         Setup production environment"
    echo "  --test         Run tests only"
    echo "  --start        Start services only"
    echo "  --stop         Stop services"
    echo "  --clean        Clean up environment"
    echo "  --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --dev      # Full development setup"
    echo "  $0 --prod     # Production deployment"
    echo "  $0 --start    # Start services"
    echo "  $0 --test     # Run tests"
}

# Clean up environment
cleanup() {
    log_info "Cleaning up environment..."
    
    # Stop services
    docker-compose down -v
    
    # Remove virtual environment
    if [[ -d "venv" ]]; then
        rm -rf venv
        log_info "Removed Python virtual environment"
    fi
    
    # Remove generated files
    rm -f config/.env
    
    log_success "Cleanup completed"
}

# Stop services
stop_services() {
    log_info "Stopping services..."
    docker-compose down
    log_success "Services stopped"
}

# Main function
main() {
    echo "🤖 Google Meet Sentiment Analysis Bot - Setup Script"
    echo "=================================================="
    
    # Parse command line arguments
    case "${1:-}" in
        --dev)
            check_root
            check_requirements
            install_system_deps
            setup_environment
            setup_python
            setup_chrome_extension
            setup_dev_tools
            setup_database
            start_services
            run_tests
            ;;
        --prod)
            check_root
            check_requirements
            setup_environment
            setup_database
            start_services
            ;;
        --test)
            run_tests
            ;;
        --start)
            start_services
            ;;
        --stop)
            stop_services
            ;;
        --clean)
            cleanup
            ;;
        --help|"")
            show_usage
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
    
    echo ""
    log_success "Setup completed successfully! 🎉"
    echo ""
    echo "Next steps:"
    echo "1. Update config/.env with your configuration"
    echo "2. Load the Chrome extension from chrome-extension/ folder"
    echo "3. Access the API at http://localhost:8000"
    echo "4. View logs at http://localhost:5601 (Kibana)"
    echo "5. Monitor metrics at http://localhost:3000 (Grafana)"
}

# Run main function
main "$@"