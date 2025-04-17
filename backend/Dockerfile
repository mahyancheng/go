# backend/Dockerfile
FROM mcr.microsoft.com/playwright/python:latest

# Install additional OS dependencies for GUI (Xvfb, VNC, supervisor, etc.)
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    net-tools \
    supervisor \
    git \
    && rm -rf /var/lib/apt/lists/*

# (Optional) Install noVNC by cloning the repository
RUN git clone https://github.com/novnc/noVNC.git /opt/novnc \
    && git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify \
    && ln -s /opt/novnc/vnc.html /opt/novnc/index.html

# Set working directory
WORKDIR /app

# Copy and install requirements (note: if browser-use is not available on PyPI, remove or use a Git URL)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers with dependencies
RUN playwright install --with-deps

# Copy application code and scripts
COPY backend/app/ ./app/
COPY backend/run_browser_task.py ./run_browser_task.py

# Copy the supervisor configuration from the backend folder
COPY backend/supervisor.conf /etc/supervisor/conf.d/supervisord.conf

# Copy frontend files (for static file serving)
COPY frontend/ ./frontend/

# Expose FastAPI (8000), noVNC (6080) and VNC (5901) ports
EXPOSE 8000 6080 5901

# Set environment variables
ENV DISPLAY=:99
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Start Supervisor which launches Xvfb, noVNC, and Uvicorn for FastAPI
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
