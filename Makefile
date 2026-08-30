.PHONY: install test run clean docker-build docker-run

VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PYTEST = $(VENV)/bin/pytest

# Core Commands
install:
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r orchestrator/requirements.txt
	$(PIP) install -r rag_layer/requirements.txt

test:
	PYTHONPATH=.:mcp_ast_server:mcp_sandbox_server:rag_layer $(PYTEST) orchestrator/tests/ mcp_ast_server/tests/ mcp_sandbox_server/tests/ rag_layer/tests/ -v

run:
	@if [ -z "$(ISSUE)" ]; then echo "Usage: make run ISSUE='Fix the null pointer bug'"; exit 1; fi
	PYTHONPATH=. $(PYTHON) main.py "$(ISSUE)"

clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf rag_layer/rag_layer/qdrant_db

# Docker Commands (Docker-out-of-Docker)
docker-build:
	docker build -t arc-agent .

docker-run:
	@if [ -z "$(ISSUE)" ]; then echo "Usage: make docker-run ISSUE='Fix bug...'"; exit 1; fi
	# Mounts the host's docker socket so the container can spin up sibling sandboxes
	docker run -it --rm \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-e OPENROUTER_API_KEY=$(OPENROUTER_API_KEY) \
		arc-agent "$(ISSUE)"
