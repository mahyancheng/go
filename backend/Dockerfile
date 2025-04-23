# backend/Dockerfile
# --- Use a specific Jammy tag AND verify Python version ---
  FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

  # Set DEBIAN_FRONTEND to noninteractive to prevent prompts during apt-get install
  ENV DEBIAN_FRONTEND=noninteractive
  
  # --- Add command to print Python version ---
  RUN echo "Checking Python version in base image:" && python --version && pip --version
  # -----------------------------------------
  
  # Install OS deps + add wget and unzip for manual package download
  # Also includes git for cloning noVNC, tzdata for timezone
  RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb \
        x11vnc \
        supervisor \
        git \
        net-tools \
        wget \
        unzip \
        tzdata \
      && rm -rf /var/lib/apt/lists/*
  
  # Set timezone to Malaysia Time (Asia/Kuala_Lumpur)
  RUN ln -fs /usr/share/zoneinfo/Asia/Kuala_Lumpur /etc/localtime && dpkg-reconfigure -f noninteractive tzdata
  
  # Clone noVNC (web client) and websockify (websocket proxy) - Still needed for Live View
  RUN echo "Cloning noVNC and websockify..." && \
      git clone https://github.com/novnc/noVNC.git /opt/novnc && \
      git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify && \
      echo "noVNC setup complete."
  
  # Set working directory inside the container
  WORKDIR /app
  
  # --- Download and Install browser-use manually using WGET ---
  # Define args for URL and expected dir name for clarity
  ARG BROWSER_USE_REPO_URL=https://github.com/HenryTran3/Browser-Use/archive/refs/heads/main.zip
  ARG BROWSER_USE_ZIP_PATH=/tmp/browser-use.zip
  ARG BROWSER_USE_EXTRACT_TMP_DIR=/tmp/browser-use-src
  ARG BROWSER_USE_EXTRACTED_DIR_NAME=Browser-Use-main # The actual dir name inside the zip
  
  RUN echo "Downloading browser-use source with wget..." && \
      wget -q ${BROWSER_USE_REPO_URL} -O ${BROWSER_USE_ZIP_PATH} && \
      echo "Download attempted."
  
  RUN echo "Testing downloaded zip file integrity..." && \
      unzip -t ${BROWSER_USE_ZIP_PATH} && \
      echo "Zip file test successful."
  
  RUN echo "Unzipping browser-use source..." && \
      mkdir -p ${BROWSER_USE_EXTRACT_TMP_DIR} && \
      unzip -q ${BROWSER_USE_ZIP_PATH} -d ${BROWSER_USE_EXTRACT_TMP_DIR} && \
      echo "Unzip complete."
  
  RUN echo "Installing browser-use from downloaded source..." && \
      pip install --no-cache-dir ${BROWSER_USE_EXTRACT_TMP_DIR}/${BROWSER_USE_EXTRACTED_DIR_NAME} && \
      echo "browser-use installed successfully."
  
  RUN echo "Cleaning up temporary browser-use files..." && \
      rm -rf ${BROWSER_USE_ZIP_PATH} ${BROWSER_USE_EXTRACT_TMP_DIR} && \
      echo "Cleanup complete."
  # -----------------------------------------------------------
  
  # Copy requirements.txt (ensure browser-use line is REMOVED from this file)
  COPY backend/requirements.txt .
  
  # Upgrade pip (good practice, run before installing requirements)
  RUN echo "Upgrading pip..." && \
      python -m pip install --upgrade pip && \
      echo "Pip upgraded."
  
  # Install the *rest* of the Python dependencies from requirements.txt
  RUN echo "Installing remaining requirements..." && \
      pip install --no-cache-dir -r requirements.txt && \
      echo "Remaining requirements installed."
  
  # Install Playwright browsers and their OS dependencies
  RUN echo "Installing Playwright browsers..." && \
      playwright install --with-deps && \
      echo "Playwright browsers installed."
  
  # Copy the rest of the backend application code
  COPY backend/app/ ./app/
  COPY backend/run_browser_task.py .
  COPY backend/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
  COPY backend/entrypoint.sh /entrypoint.sh
  RUN chmod +x /entrypoint.sh
  
  # Copy the frontend files
  COPY backend/frontend/ ./frontend/
  RUN mkdir -p /app/tasks
  
  # Expose ports
  EXPOSE 8000 6080 5901
  
  # Set environment variables
  ENV DISPLAY=:99
  ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
  
  # Run the entrypoint script
  ENTRYPOINT ["/entrypoint.sh"]