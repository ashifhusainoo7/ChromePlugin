#!/bin/bash

# Google Meet Sentiment Analysis Bot - Installation Script
# This script installs all necessary dependencies and sets up the environment

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

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
            VER=$VERSION_ID
        else
            OS="unknown"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        VER=$(sw_vers -productVersion)
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        OS="windows"
        VER="unknown"
    else
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    log_info "Detected OS: $OS $VER"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root for security reasons"
        log_error "Please run as a regular user with sudo privileges"
        exit 1
    fi
}

# Install Python 3.11+
install_python() {
    log_info "Installing Python 3.11+..."
    
    case $OS in
        "ubuntu"|"debian")
            # Add deadsnakes PPA for latest Python versions
            sudo apt update
            sudo apt install -y software-properties-common
            sudo add-apt-repository -y ppa:deadsnakes/ppa
            sudo apt update
            sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
            
            # Set Python 3.11 as default python3
            sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
            ;;
        "centos"|"rhel"|"fedora")
            # Install Python 3.11 from source or EPEL
            sudo dnf install -y python3.11 python3.11-pip python3.11-devel
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                brew install python@3.11
                brew link python@3.11
            else
                log_error "Homebrew is required on macOS. Please install it first."
                exit 1
            fi
            ;;
        *)
            log_error "Automatic Python installation not supported for $OS"
            log_error "Please install Python 3.11+ manually"
            exit 1
            ;;
    esac
    
    # Verify Python installation
    if python3.11 --version &> /dev/null; then
        log_success "Python 3.11 installed successfully"
    else
        log_error "Python 3.11 installation failed"
        exit 1
    fi
}

# Install Node.js and npm
install_nodejs() {
    log_info "Installing Node.js 16+..."
    
    case $OS in
        "ubuntu"|"debian")
            # Install Node.js 16 LTS
            curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
            sudo apt-get install -y nodejs
            ;;
        "centos"|"rhel"|"fedora")
            # Install Node.js 16 LTS
            curl -fsSL https://rpm.nodesource.com/setup_16.x | sudo bash -
            sudo dnf install -y nodejs npm
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                brew install node@16
                brew link node@16
            else
                log_error "Homebrew is required on macOS"
                exit 1
            fi
            ;;
        *)
            log_error "Automatic Node.js installation not supported for $OS"
            exit 1
            ;;
    esac
    
    # Verify Node.js installation
    if node --version &> /dev/null && npm --version &> /dev/null; then
        log_success "Node.js installed successfully: $(node --version)"
    else
        log_error "Node.js installation failed"
        exit 1
    fi
}

# Install Docker and Docker Compose
install_docker() {
    log_info "Installing Docker and Docker Compose..."
    
    case $OS in
        "ubuntu"|"debian")
            # Install Docker
            sudo apt-get update
            sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
            
            # Add Docker's official GPG key
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
            
            # Set up Docker repository
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            # Install Docker Engine
            sudo apt-get update
            sudo apt-get install -y docker-ce docker-ce-cli containerd.io
            
            # Install Docker Compose
            sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            sudo chmod +x /usr/local/bin/docker-compose
            
            # Add user to docker group
            sudo usermod -aG docker $USER
            ;;
        "centos"|"rhel"|"fedora")
            # Install Docker
            sudo dnf remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-selinux docker-engine-selinux docker-engine
            sudo dnf install -y dnf-plugins-core
            sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
            sudo dnf install -y docker-ce docker-ce-cli containerd.io
            
            # Install Docker Compose
            sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            sudo chmod +x /usr/local/bin/docker-compose
            
            # Start and enable Docker
            sudo systemctl start docker
            sudo systemctl enable docker
            
            # Add user to docker group
            sudo usermod -aG docker $USER
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                brew install --cask docker
                log_warning "Please start Docker Desktop manually after installation"
            else
                log_error "Homebrew is required on macOS"
                exit 1
            fi
            ;;
        *)
            log_error "Automatic Docker installation not supported for $OS"
            exit 1
            ;;
    esac
    
    # Verify Docker installation
    if docker --version &> /dev/null && docker-compose --version &> /dev/null; then
        log_success "Docker installed successfully: $(docker --version)"
        log_success "Docker Compose installed successfully: $(docker-compose --version)"
    else
        log_error "Docker installation failed"
        exit 1
    fi
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    
    case $OS in
        "ubuntu"|"debian")
            sudo apt-get update
            sudo apt-get install -y \
                build-essential \
                curl \
                wget \
                git \
                vim \
                htop \
                unzip \
                software-properties-common \
                apt-transport-https \
                ca-certificates \
                gnupg \
                lsb-release \
                ffmpeg \
                libpq-dev \
                postgresql-client \
                redis-tools \
                python3-dev \
                python3-pip \
                python3-venv
            ;;
        "centos"|"rhel"|"fedora")
            sudo dnf update -y
            sudo dnf groupinstall -y "Development Tools"
            sudo dnf install -y \
                curl \
                wget \
                git \
                vim \
                htop \
                unzip \
                ffmpeg \
                postgresql-devel \
                postgresql \
                redis \
                python3-devel \
                python3-pip
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                brew update
                brew install \
                    curl \
                    wget \
                    git \
                    vim \
                    htop \
                    unzip \
                    ffmpeg \
                    postgresql \
                    redis
            else
                log_error "Homebrew is required on macOS"
                exit 1
            fi
            ;;
        *)
            log_error "Automatic system dependencies installation not supported for $OS"
            exit 1
            ;;
    esac
    
    log_success "System dependencies installed successfully"
}

# Install Google Chrome
install_chrome() {
    log_info "Installing Google Chrome..."
    
    case $OS in
        "ubuntu"|"debian")
            # Download and install Chrome
            wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
            sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
            sudo apt-get update
            sudo apt-get install -y google-chrome-stable
            ;;
        "centos"|"rhel"|"fedora")
            # Download and install Chrome
            sudo dnf install -y wget
            wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
            sudo dnf install -y ./google-chrome-stable_current_x86_64.rpm
            rm -f google-chrome-stable_current_x86_64.rpm
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                brew install --cask google-chrome
            else
                log_warning "Please install Google Chrome manually from https://www.google.com/chrome/"
            fi
            ;;
        *)
            log_warning "Automatic Chrome installation not supported for $OS"
            log_warning "Please install Google Chrome manually"
            ;;
    esac
    
    # Verify Chrome installation
    if google-chrome --version &> /dev/null || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --version &> /dev/null; then
        log_success "Google Chrome installed successfully"
    else
        log_warning "Chrome installation verification failed - please check manually"
    fi
}

# Install ChromeDriver
install_chromedriver() {
    log_info "Installing ChromeDriver..."
    
    # Get latest ChromeDriver version
    CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)
    
    case $OS in
        "ubuntu"|"debian"|"centos"|"rhel"|"fedora")
            # Download ChromeDriver for Linux
            wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
            sudo unzip -o /tmp/chromedriver.zip -d /usr/local/bin/
            sudo chmod +x /usr/local/bin/chromedriver
            rm -f /tmp/chromedriver.zip
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                brew install chromedriver
            else
                # Manual installation for macOS
                wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_mac64.zip"
                sudo unzip -o /tmp/chromedriver.zip -d /usr/local/bin/
                sudo chmod +x /usr/local/bin/chromedriver
                rm -f /tmp/chromedriver.zip
            fi
            ;;
        *)
            log_warning "Automatic ChromeDriver installation not supported for $OS"
            ;;
    esac
    
    # Verify ChromeDriver installation
    if chromedriver --version &> /dev/null; then
        log_success "ChromeDriver installed successfully: $(chromedriver --version)"
    else
        log_warning "ChromeDriver installation verification failed"
    fi
}

# Install PostgreSQL
install_postgresql() {
    log_info "Installing PostgreSQL..."
    
    case $OS in
        "ubuntu"|"debian")
            sudo apt-get update
            sudo apt-get install -y postgresql postgresql-contrib
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
        "centos"|"rhel"|"fedora")
            sudo dnf install -y postgresql-server postgresql-contrib
            sudo postgresql-setup --initdb
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                brew install postgresql
                brew services start postgresql
            else
                log_error "Homebrew is required on macOS"
                exit 1
            fi
            ;;
        *)
            log_warning "Automatic PostgreSQL installation not supported for $OS"
            ;;
    esac
    
    log_success "PostgreSQL installation completed"
}

# Install Redis
install_redis() {
    log_info "Installing Redis..."
    
    case $OS in
        "ubuntu"|"debian")
            sudo apt-get update
            sudo apt-get install -y redis-server
            sudo systemctl start redis-server
            sudo systemctl enable redis-server
            ;;
        "centos"|"rhel"|"fedora")
            sudo dnf install -y redis
            sudo systemctl start redis
            sudo systemctl enable redis
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                brew install redis
                brew services start redis
            else
                log_error "Homebrew is required on macOS"
                exit 1
            fi
            ;;
        *)
            log_warning "Automatic Redis installation not supported for $OS"
            ;;
    esac
    
    log_success "Redis installation completed"
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p uploads
    mkdir -p backups
    mkdir -p chrome-extension/assets/images
    
    # Create placeholder icon files
    for size in 16 32 48 128; do
        if [[ ! -f "chrome-extension/assets/images/icon-${size}.png" ]]; then
            # Create a simple colored square as placeholder
            # In production, replace with actual icon files
            echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" | base64 -d > "chrome-extension/assets/images/icon-${size}.png" 2>/dev/null || echo "Placeholder icon ${size}x${size}" > "chrome-extension/assets/images/icon-${size}.png"
        fi
    done
    
    log_success "Directories created successfully"
}

# Install Python dependencies
install_python_deps() {
    log_info "Installing Python dependencies..."
    
    # Create virtual environment
    if [[ ! -d "venv" ]]; then
        python3.11 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    cd backend
    pip install -r requirements.txt
    cd ..
    
    log_success "Python dependencies installed successfully"
}

# Setup Git hooks (optional)
setup_git_hooks() {
    if [[ -d ".git" ]]; then
        log_info "Setting up Git hooks..."
        
        # Create pre-commit hook
        cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Run Python code formatting and linting before commit

source venv/bin/activate
cd backend

# Run black formatter
black --check .

# Run isort
isort --check-only .

# Run flake8 linter
flake8 .

# Run mypy type checker
mypy app/
EOF
        
        chmod +x .git/hooks/pre-commit
        log_success "Git hooks setup completed"
    fi
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."
    
    local errors=0
    
    # Check Python
    if ! python3.11 --version &> /dev/null; then
        log_error "Python 3.11 not found"
        ((errors++))
    fi
    
    # Check Node.js
    if ! node --version &> /dev/null; then
        log_error "Node.js not found"
        ((errors++))
    fi
    
    # Check Docker
    if ! docker --version &> /dev/null; then
        log_error "Docker not found"
        ((errors++))
    fi
    
    # Check Docker Compose
    if ! docker-compose --version &> /dev/null; then
        log_error "Docker Compose not found"
        ((errors++))
    fi
    
    # Check Chrome
    if ! google-chrome --version &> /dev/null && ! "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --version &> /dev/null; then
        log_warning "Google Chrome not found or not accessible"
    fi
    
    # Check ChromeDriver
    if ! chromedriver --version &> /dev/null; then
        log_warning "ChromeDriver not found"
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_success "All core dependencies verified successfully!"
    else
        log_error "$errors critical dependencies missing"
        return 1
    fi
}

# Show post-installation instructions
show_post_install() {
    echo ""
    log_success "Installation completed successfully! 🎉"
    echo ""
    echo "Next steps:"
    echo "1. Log out and log back in (or run 'newgrp docker') to use Docker without sudo"
    echo "2. Copy config/.env.example to config/.env and update with your settings"
    echo "3. Run './scripts/setup.sh --dev' to start the development environment"
    echo "4. Load the Chrome extension from chrome-extension/ folder"
    echo ""
    echo "Useful commands:"
    echo "  ./scripts/setup.sh --dev    # Setup development environment"
    echo "  ./scripts/setup.sh --prod   # Setup production environment"
    echo "  docker-compose up -d        # Start all services"
    echo "  docker-compose logs -f      # View logs"
    echo ""
    echo "Access points after setup:"
    echo "  API: http://localhost:8000"
    echo "  Grafana: http://localhost:3000 (admin/admin123)"
    echo "  Kibana: http://localhost:5601"
    echo "  Prometheus: http://localhost:9090"
    echo ""
}

# Main installation function
main() {
    echo "🔧 Google Meet Sentiment Analysis Bot - Installation Script"
    echo "=========================================================="
    echo ""
    
    # Check if running as root
    check_root
    
    # Detect operating system
    detect_os
    
    # Install components
    log_info "Starting installation process..."
    
    install_system_deps
    install_python
    install_nodejs
    install_docker
    install_chrome
    install_chromedriver
    install_postgresql
    install_redis
    create_directories
    install_python_deps
    setup_git_hooks
    
    # Verify installation
    if verify_installation; then
        show_post_install
    else
        log_error "Installation completed with errors. Please check the logs above."
        exit 1
    fi
}

# Run main function
main "$@"