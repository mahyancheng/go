# Use an official Python runtime as the base image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# (Optional) Install Playwright browsers if you use browser automation
# RUN playwright install --with-deps

# Copy the backend code
COPY backend/app ./app

# Copy the frontend static files
COPY frontend ./frontend

# Expose the port FastAPI will run on
EXPOSE 8000

# Run the FastAPI app; adjust "--reload" only for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
