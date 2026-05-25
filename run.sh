#!/bin/bash

#
# Run PS2-VMC-GUI with virtual environment
# Automatically activates venv and runs the Python GUI
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
VENV_ACTIVATE="$VENV_DIR/bin/activate"
GUI_SCRIPT="$SCRIPT_DIR/vmc_gui.py"

# Check if venv exists
if [[ ! -d "$VENV_DIR" ]]; then
    echo "❌ Virtual environment not found at: $VENV_DIR"
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    
    if [[ ! $? -eq 0 ]]; then
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
    
    echo "✅ Virtual environment created"
    echo ""
    echo "Installing dependencies..."
    source "$VENV_ACTIVATE"
    pip install --upgrade pip > /dev/null 2>&1
    pip install -r "$SCRIPT_DIR/requirements.txt" > /dev/null 2>&1
    echo "✅ Dependencies installed"
fi

# Check if GUI script exists
if [[ ! -f "$GUI_SCRIPT" ]]; then
    echo "❌ GUI script not found at: $GUI_SCRIPT"
    exit 1
fi

# Activate virtual environment and run GUI
source "$VENV_ACTIVATE"
python3 "$GUI_SCRIPT"
