# Use a slim Python 3.12 image
FROM python:3.12-slim

WORKDIR /app

# Install docker CLI (so the container can talk to the mounted docker.sock)
RUN apt-get update && apt-get install -y docker.io gcc build-essential && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY orchestrator/requirements.txt /app/orchestrator/requirements.txt
COPY rag_layer/requirements.txt /app/rag_layer/requirements.txt
COPY mcp_ast_server/requirements.txt /app/mcp_ast_server/requirements.txt
COPY mcp_sandbox_server/requirements.txt /app/mcp_sandbox_server/requirements.txt

# Install all module dependencies
RUN pip install --no-cache-dir -r orchestrator/requirements.txt -r rag_layer/requirements.txt

# Copy the rest of the application
COPY . /app/

# Set Python Path so the local packages resolve correctly
ENV PYTHONPATH="/app:/app/mcp_ast_server:/app/mcp_sandbox_server:/app/rag_layer"

# Set the entrypoint to our CLI
ENTRYPOINT ["python", "main.py"]
