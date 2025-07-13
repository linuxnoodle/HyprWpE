#!/bin/bash

# Debug script to test PID tracking issue
echo "=== PID Tracking Debug Script ==="
echo "Testing scenario: Set wallpaper, open/close GUI and terminal, then try to stop"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PID_FILE="/tmp/hyprpaper-we.pid"

# Function to check PID file
check_pid_file() {
    echo -e "${YELLOW}Checking PID file...${NC}"
    if [ -f "$PID_FILE" ]; then
        echo -e "${GREEN}PID file exists at: $PID_FILE${NC}"
        local pid=$(cat "$PID_FILE")
        echo "PID in file: $pid"
        
        # Check if process is actually running
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${GREEN}Process $pid is running${NC}"
            ps -fp $pid
        else
            echo -e "${RED}Process $pid is NOT running (zombie PID file)${NC}"
        fi
    else
        echo -e "${RED}PID file does not exist${NC}"
    fi
    echo ""
}

# Function to check running wallpaper processes
check_wallpaper_processes() {
    echo -e "${YELLOW}Checking for wallpaper processes...${NC}"
    
    # Check for mpvpaper
    local mpv_pids=$(pgrep -f "mpvpaper")
    if [ -n "$mpv_pids" ]; then
        echo -e "${GREEN}Found mpvpaper processes:${NC}"
        for pid in $mpv_pids; do
            ps -fp $pid
        done
    else
        echo "No mpvpaper processes found"
    fi
    
    # Check for web_viewer
    local web_pids=$(pgrep -f "web_viewer.py")
    if [ -n "$web_pids" ]; then
        echo -e "${GREEN}Found web_viewer.py processes:${NC}"
        for pid in $web_pids; do
            ps -fp $pid
        done
    else
        echo "No web_viewer.py processes found"
    fi
    echo ""
}

# Function to monitor file changes
monitor_pid_file() {
    echo -e "${YELLOW}Monitoring PID file for 5 seconds...${NC}"
    local count=0
    while [ $count -lt 5 ]; do
        if [ -f "$PID_FILE" ]; then
            local current_pid=$(cat "$PID_FILE" 2>/dev/null)
            local mod_time=$(stat -c %Y "$PID_FILE" 2>/dev/null)
            echo "[$count] PID file exists - PID: $current_pid, Modified: $(date -d @$mod_time '+%H:%M:%S')"
        else
            echo "[$count] PID file missing"
        fi
        sleep 1
        ((count++))
    done
    echo ""
}

# Main test sequence
echo "=== Initial State ==="
check_pid_file
check_wallpaper_processes

echo -e "${YELLOW}Test Instructions:${NC}"
echo "1. Run a wallpaper using: ./hyprpaper-we.sh <wallpaper_id>"
echo "2. Open and close the GUI (python gui.py)"
echo "3. Open and close a terminal"
echo "4. Try to stop the wallpaper: ./hyprpaper-we.sh stop"
echo ""
echo "After each step, press Enter to check the current state..."

read -p "Press Enter after setting a wallpaper..."
echo -e "\n${YELLOW}=== After Setting Wallpaper ===${NC}"
check_pid_file
check_wallpaper_processes

read -p "Press Enter after opening/closing GUI..."
echo -e "\n${YELLOW}=== After GUI Open/Close ===${NC}"
check_pid_file
check_wallpaper_processes

read -p "Press Enter after opening/closing terminal..."
echo -e "\n${YELLOW}=== After Terminal Open/Close ===${NC}"
check_pid_file
check_wallpaper_processes

echo -e "\n${YELLOW}=== Testing Stop Command ===${NC}"
echo "Running: ./hyprpaper-we.sh stop"
./hyprpaper-we.sh stop

echo -e "\n${YELLOW}=== Final State ===${NC}"
check_pid_file
check_wallpaper_processes

# Additional debugging
echo -e "\n${YELLOW}=== Additional Debug Info ===${NC}"
echo "Checking for any stale lock files or temp files:"
ls -la /tmp/hyprpaper-we* 2>/dev/null || echo "No hyprpaper-we files in /tmp"

echo -e "\n${YELLOW}=== Process Tree ===${NC}"
echo "Looking for parent-child relationships:"
pstree -p | grep -E "(mpvpaper|web_viewer|python)" || echo "No relevant processes in tree"