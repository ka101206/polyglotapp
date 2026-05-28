#!/bin/bash
set -e

# Start Xvfb (Virtual Screen)
# Resolution: 1280x800 with 24-bit color
Xvfb :99 -screen 0 1280x800x24 &
export DISPLAY=:99

# Wait for Xvfb to be ready
sleep 2

# Start Fluxbox (Window Manager) for window borders and titlebars
fluxbox -display :99 &

# Start x11vnc (VNC Server attached to the virtual screen)
x11vnc -display :99 -nopw -listen localhost -xkb -ncache 10 -ncache_cr -forever &

# Start noVNC (HTML5 VNC Client on port 8080)
/usr/share/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 8080 &

echo "=========================================================="
echo "🌐 GUI is ready! Open http://localhost:8080/vnc.html in your browser."
echo "=========================================================="

# Start the Python Application
python main.py
