#!/bin/bash
# Token Telemetry Installation Script
# This script installs the token-telemetry package and its dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print error messages
error_msg() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to print success messages
success_msg() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Function to print warning messages
warning_msg() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to print info messages
info_msg() {
    echo "[INFO] $1"
}

# Check if Python 3.11+ is available
check_python() {
    info_msg "Checking Python version..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        info_msg "Found Python $PYTHON_VERSION"
        
        # Check version is >= 3.11
        MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
        
        if [ "$MAJOR" -lt 3 ] || [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]; then
            error_msg "Python 3.11 or higher is required. Found Python $PYTHON_VERSION"
            exit 1
        fi
    else
        error_msg "Python 3 is not installed. Please install Python 3.11+ before proceeding."
        exit 1
    fi
    success_msg "Python version check passed"
}

# Install the package
install_package() {
    info_msg "Installing token-telemetry package..."
    
    # Check if we're in the project directory
    if [ -f "pyproject.toml" ]; then
        info_msg "Installing in development mode from current directory..."
        python3 -m pip install -e .
    else
        info_msg "Installing from PyPI..."
        python3 -m pip install token-telemetry
    fi
    
    success_msg "Package installed successfully"
}

# Verify installation
verify_installation() {
    info_msg "Verifying installation..."
    
    # Check if entry points are available
    if command -v token-telemetry &> /dev/null; then
        success_msg "token-telemetry command is available"
    else
        error_msg "token-telemetry command is not available"
        exit 1
    fi
    
    if command -v telemetry-proxy &> /dev/null; then
        success_msg "telemetry-proxy command is available"
    else
        warning_msg "telemetry-proxy command is not available"
    fi
    
    if command -v telemetry-report &> /dev/null; then
        success_msg "telemetry-report command is available"
    else
        warning_msg "telemetry-report command is not available"
    fi
    
    # Check Python imports
    if python3 -c "import token_telemetry; print('Import successful')" 2> /dev/null; then
        success_msg "Python import test passed"
    else
        error_msg "Python import test failed"
        exit 1
    fi
}

# Create configuration directory
create_config_dir() {
    info_msg "Creating configuration directory..."
    
    # Default config directory
    CONFIG_DIR="$HOME/.config/token-telemetry"
    
    if [ ! -d "$CONFIG_DIR" ]; then
        mkdir -p "$CONFIG_DIR"
        success_msg "Created configuration directory: $CONFIG_DIR"
    else
        info_msg "Configuration directory already exists: $CONFIG_DIR"
    fi
    
    # Copy default configs if they don't exist
    if [ -f "config/default_config.yaml" ] && [ ! -f "$CONFIG_DIR/config.yaml" ]; then
        cp "config/default_config.yaml" "$CONFIG_DIR/config.yaml"
        info_msg "Copied default configuration to $CONFIG_DIR/config.yaml"
    fi
    
    if [ -f "config/default_pricing.yaml" ] && [ ! -f "$CONFIG_DIR/pricing.yaml" ]; then
        cp "config/default_pricing.yaml" "$CONFIG_DIR/pricing.yaml"
        info_msg "Copied default pricing configuration to $CONFIG_DIR/pricing.yaml"
    fi
}

# Main installation function
main() {
    echo "=========================================="
    echo "Token Telemetry Installation"
    echo "=========================================="
    echo ""
    
    check_python
    echo ""
    
    install_package
    echo ""
    
    verify_installation
    echo ""
    
    create_config_dir
    echo ""
    
    echo "=========================================="
    echo "Installation Complete!"
    echo "=========================================="
    echo ""
    echo "To start the proxy server:"
    echo "  token-telemetry proxy"
    echo ""
    echo "To generate a report:"
    echo "  token-telemetry report"
    echo ""
    echo "For more options:"
    echo "  token-telemetry --help"
}

# Run main function
main "$@"
