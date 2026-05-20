#!/bin/bash
# Token Telemetry Update Script
# This script updates the token-telemetry package to the latest version

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

# Check current version
check_current_version() {
    info_msg "Checking current version..."
    
    if python3 -c "import token_telemetry; print(token_telemetry.__version__)" 2> /dev/null; then
        CURRENT_VERSION=$(python3 -c "import token_telemetry; print(token_telemetry.__version__)")
        info_msg "Current version: $CURRENT_VERSION"
    else
        CURRENT_VERSION="Not installed"
        info_msg "Package is not currently installed"
    fi
}

# Update the package
update_package() {
    info_msg "Updating token-telemetry package..."
    
    # Check if we're in the project directory
    if [ -f "pyproject.toml" ]; then
        info_msg "Detected project directory. Pulling latest changes..."
        
        # Check if git is available
        if command -v git &> /dev/null; then
            git pull origin main 2> /dev/null || git pull origin master 2> /dev/null || {
                warning_msg "Could not pull latest changes. Using current state."
            }
        fi
        
        info_msg "Reinstalling in development mode..."
        python3 -m pip install -e . --upgrade
    else
        info_msg "Installing/upgrading from PyPI..."
        python3 -m pip install --upgrade token-telemetry
    fi
    
    success_msg "Package updated successfully"
}

# Get new version
get_new_version() {
    if python3 -c "import token_telemetry; print(token_telemetry.__version__)" 2> /dev/null; then
        NEW_VERSION=$(python3 -c "import token_telemetry; print(token_telemetry.__version__)")
        success_msg "Updated to version: $NEW_VERSION"
    else
        error_msg "Failed to get new version"
        exit 1
    fi
}

# Verify update
verify_update() {
    info_msg "Verifying update..."
    
    # Check if entry points are available
    if command -v token-telemetry &> /dev/null; then
        success_msg "token-telemetry command is available"
    else
        error_msg "token-telemetry command is not available"
        exit 1
    fi
    
    # Check Python imports
    if python3 -c "import token_telemetry" 2> /dev/null; then
        success_msg "Python import test passed"
    else
        error_msg "Python import test failed"
        exit 1
    fi
}

# Check for updates (PyPI)
check_for_updates() {
    info_msg "Checking for available updates..."
    
    if command -v pip &> /dev/null; then
        # Get latest version from PyPI
        LATEST_VERSION=$(pip index versions token-telemetry 2> /dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)
        
        if [ -z "$LATEST_VERSION" ]; then
            warning_msg "Could not determine latest version from PyPI"
        else
            info_msg "Latest version available on PyPI: $LATEST_VERSION"
            
            if [ "$CURRENT_VERSION" != "$LATEST_VERSION" ]; then
                info_msg "Update available: $CURRENT_VERSION -> $LATEST_VERSION"
            else
                info_msg "Package is up to date"
            fi
        fi
    fi
}

# Main update function
main() {
    echo "=========================================="
    echo "Token Telemetry Update"
    echo "=========================================="
    echo ""
    
    check_current_version
    echo ""
    
    check_for_updates
    echo ""
    
    update_package
    echo ""
    
    get_new_version
    echo ""
    
    verify_update
    echo ""
    
    echo "=========================================="
    echo "Update Complete!"
    echo "=========================================="
    echo ""
    echo "To verify the update worked:"
    echo "  token-telemetry --help"
}

# Run main function
main "$@"
