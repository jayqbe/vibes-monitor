#!/bin/bash
# Token Telemetry Uninstallation Script
# This script removes the token-telemetry package and its files

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

# Uninstall the package
uninstall_package() {
    info_msg "Uninstalling token-telemetry package..."
    
    # Try to uninstall using pip
    if python3 -m pip uninstall -y token-telemetry 2> /dev/null; then
        success_msg "Package uninstalled successfully"
    else
        warning_msg "Package was not found or already uninstalled"
    fi
}

# Remove configuration directory
remove_config_dir() {
    info_msg "Removing configuration directory..."
    
    CONFIG_DIR="$HOME/.config/token-telemetry"
    
    if [ -d "$CONFIG_DIR" ]; then
        info_msg "Found configuration directory: $CONFIG_DIR"
        read -p "Do you want to remove the configuration directory and all its contents? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$CONFIG_DIR"
            success_msg "Configuration directory removed"
        else
            info_msg "Configuration directory preserved"
        fi
    else
        info_msg "No configuration directory found"
    fi
}

# Remove database files
remove_database_files() {
    info_msg "Removing database files..."
    
    DB_FILES=("telemetry.db" "telemetry.db-wal" "telemetry.db-shm")
    
    for db_file in "${DB_FILES[@]}"; do
        if [ -f "$db_file" ]; then
            info_msg "Found database file: $db_file"
            read -p "Do you want to remove $db_file? [y/N] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm "$db_file"
                success_msg "Database file $db_file removed"
            else
                info_msg "Database file $db_file preserved"
            fi
        fi
    done
}

# Remove log files
remove_log_files() {
    info_msg "Removing log files..."
    
    LOG_FILES=("telemetry.log")
    
    for log_file in "${LOG_FILES[@]}"; do
        if [ -f "$log_file" ]; then
            info_msg "Found log file: $log_file"
            read -p "Do you want to remove $log_file? [y/N] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm "$log_file"
                success_msg "Log file $log_file removed"
            else
                info_msg "Log file $log_file preserved"
            fi
        fi
    done
}

# Verify uninstallation
verify_uninstallation() {
    info_msg "Verifying uninstallation..."
    
    # Check if entry points are still available
    if command -v token-telemetry &> /dev/null; then
        warning_msg "token-telemetry command is still available. Uninstallation may not be complete."
    else
        success_msg "token-telemetry command is no longer available"
    fi
    
    # Check Python imports
    if python3 -c "import token_telemetry" 2> /dev/null; then
        warning_msg "Python import still works. Package may not be fully uninstalled."
    else
        success_msg "Python import test passed (package is uninstalled)"
    fi
}

# Main uninstallation function
main() {
    echo "=========================================="
    echo "Token Telemetry Uninstallation"
    echo "=========================================="
    echo ""
    
    uninstall_package
    echo ""
    
    remove_database_files
    echo ""
    
    remove_log_files
    echo ""
    
    remove_config_dir
    echo ""
    
    verify_uninstallation
    echo ""
    
    echo "=========================================="
    echo "Uninstallation Complete!"
    echo "=========================================="
}

# Run main function
main "$@"
