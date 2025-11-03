#!/usr/bin/env bash

# wifitool/setup.sh
# Main starter script for the wifitool project.
#
# This script will:
# 1. Check for all required system dependencies.
# 2. Create a Python virtual environment (.venv) if it doesn't exist.
# 3. Install required Python packages (Flask, pycryptodome) into the venv.
# 4. Pass all arguments to main.py, adding 'sudo' for network commands.

set -e # Exit immediately if any command fails

# --- Configuration ---
VENV_DIR=".venv"
PYTHON_EXEC="$VENV_DIR/bin/python"
PIP_EXEC="$VENV_DIR/bin/pip"
REQ_FILE="requirements.txt"

# --- Color Codes ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# --- 1. System Dependency Check ---
echo -e "${GREEN}Checking system dependencies...${NC}"

# This list contains the *package names* that provide the tools
# This is what 'apt' will install
PACKAGES_TO_INSTALL=("hostapd" "dnsmasq" "iptables" "iproute2" "iw" "network-manager" "python3-venv")

# This list contains the *commands* we check for
REQUIRED_TOOLS=("hostapd" "dnsmasq" "iptables" "ip" "iw" "nmcli" "python3")
MISSING_TOOLS=()

for tool in "${REQUIRED_TOOLS[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
        MISSING_TOOLS+=("$tool")
    fi
done

# Also check if the python 'venv' module is available
if ! python3 -m venv --help &> /dev/null; then
    MISSING_TOOLS+=("python3-venv")
fi

if [ ${#MISSING_TOOLS[@]} -ne 0 ]; then
    echo -e "${YELLOW}Warning: The following required dependencies are missing:${NC}"
    for tool in "${MISSING_TOOLS[@]}"; do
        echo -e "  - $tool"
    done
    
    # Check if 'apt' is available
    if command -v apt &> /dev/null; then
        echo "" # new line
        read -p "Attempt to install them using 'apt'? (y/n) " response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            echo -e "${GREEN}Running: sudo apt update && sudo apt install -y ${PACKAGES_TO_INSTALL[*]}${NC}"
            if ! sudo apt update; then
                echo -e "${RED}Failed to run 'apt update'. Please check your internet connection and permissions.${NC}"
                exit 1
            fi
            if ! sudo apt install -y "${PACKAGES_TO_INSTALL[@]}"; then
                 echo -e "${RED}Failed to install packages. Please try installing them manually.${NC}"
                 exit 1
            fi
            echo -e "${GREEN}Dependencies installed. Re-checking...${NC}"
            
            # Re-check after installation
            MISSING_TOOLS=()
            for tool in "${REQUIRED_TOOLS[@]}"; do
                if ! command -v "$tool" &> /dev/null; then
                    MISSING_TOOLS+=("$tool")
                fi
            done
            if ! python3 -m venv --help &> /dev/null; then
                MISSING_TOOLS+=("python3-venv")
            fi

            if [ ${#MISSING_TOOLS[@]} -ne 0 ]; then
                 echo -e "${RED}Error: Even after install, the following tools are missing:${NC}"
                 for tool in "${MISSING_TOOLS[@]}"; do echo -e "  - $tool"; done
                 exit 1
            fi

        else
            echo -e "${RED}Installation skipped. Exiting.${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Error: 'apt' package manager not found.${NC}"
        echo "Please install the following packages manually:"
        echo "  ${PACKAGES_TO_INSTALL[*]}"
        exit 1
    fi
fi

echo -e "${GREEN}All system dependencies are met.${NC}"


# --- 2. Virtual Environment Setup ---
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${GREEN}Creating Python virtual environment at '$VENV_DIR'...${NC}"
    python3 -m venv "$VENV_DIR"
    
    echo -e "${GREEN}Installing Python dependencies from $REQ_FILE...${NC}"
    if [ ! -f "$REQ_FILE" ]; then
        echo -e "${RED}Error: $REQ_FILE not found!${NC}"
        exit 1
    fi
    "$PIP_EXEC" install -r "$REQ_FILE"
    echo -e "${GREEN}Python setup complete.${NC}"
else
    echo -e "${GREEN}Virtual environment is ready.${NC}"
fi


# --- 3. Command Execution ---
if [ $# -eq 0 ]; then
    echo -e "\nUsage: ./setup.sh <command>"
    echo -e "Example: ./setup.sh start\n"
    "$PYTHON_EXEC" main.py help
    exit 0
fi

CMD="$1"

# Check if the command needs root privileges
if [ "$CMD" = "start" ] || [ "$CMD" = "stop" ] || [ "$CMD" = "prepare" ]; then
    # Check if we are already root
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}Network command '$CMD' requires root. Re-running with sudo exec...${NC}"
        # --- MODIFIED: Added exec ---
        # Re-run the python script with sudo, passing all arguments
        exec sudo "$PYTHON_EXEC" main.py "$@"
    else
        # We are already root, just run the command
        # --- MODIFIED: Added exec ---
        exec "$PYTHON_EXEC" main.py "$@"
    fi
else
    # Not a network command (e.g., status, choose-iface, help)
    # Run without sudo
    # --- MODIFIED: Added exec ---
    exec "$PYTHON_EXEC" main.py "$@"
fi