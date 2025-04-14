# Use an official Python runtime as the base image [cite: 156]
FROM python:3.11-slim-buster

# Set the working directory in the container [cite: 156]
WORKDIR /app

# Copy the requirements file into the container [cite: 156]
# Assumes Dockerfile is in the root 'your_app/' directory
COPY backend/requirements.txt ./

# Install the backend dependencies [cite: 157]
RUN pip install --no-cache-dir -r requirements.txt

# Optional: Install Playwright browsers if using browser-use direct embedding
# RUN playwright install --with-deps

# Copy the backend application code into the container [cite: 157]
# Copies the entire 'backend/app' directory to '/app/app' inside the container
COPY backend/app ./app

# Expose the port that the FastAPI application will run on [cite: 158]
EXPOSE 8000

# Define the command to run the application using Uvicorn [cite: 158]
# The '--reload' flag is useful for development but should be removed for production.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]