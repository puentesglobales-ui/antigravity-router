# Lightweight Python Image
FROM python:3.9-slim

# Working Directory
WORKDIR /app

# Copy Requirements & Install (Cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Codebase
COPY . .

# Environment Defaults
ENV PORT=8000

# Run API
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
