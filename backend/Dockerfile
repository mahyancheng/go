# backend/Dockerfile
# Use a newer Python base image based on Debian Bookworm
FROM python:3.11-slim-bookworm

# Install OS dependencies needed by Playwright browsers
# Reference: https://playwright.dev/docs/docker
# Dependencies might differ slightly between debian versions, but playwright attempts to handle it.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libexpat1 \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker cache
# Assumes Dockerfile is run with build context set to 'mahyancheng-go' root
COPY backend/requirements.txt ./requirements.txt

# Install Python dependencies
# Note: Your requirements.txt includes gradio, which might not be needed if using FastAPI main.py
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and their OS dependencies
# This step downloads browser binaries into the image
RUN playwright install --with-deps

# Copy the rest of the backend application code
# Copy contents of backend/app into /app/app
COPY backend/app/ ./app/
# Copy run_browser_task.py into /app
COPY backend/run_browser_task.py ./run_browser_task.py
# Copy frontend files into /app/frontend (if served by FastAPI)
COPY frontend ./frontend/

# Expose the port that the FastAPI application will run on
EXPOSE 8000

# Define the command to run the application using Uvicorn
# Remove --reload for production/stable runs
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Keep --reload for development watching
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
