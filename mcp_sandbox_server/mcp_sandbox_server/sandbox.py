import docker
import base64
import os

try:
    client = docker.from_env()
except Exception:
    client = None

current_container = None
WORKSPACE_DIR = "/workspace"

def get_or_create_container():
    global current_container
    if client is None:
        raise RuntimeError("Docker daemon is not running or accessible.")
        
    if current_container is not None:
        try:
            current_container.reload()
            if current_container.status == 'running':
                return current_container
        except docker.errors.NotFound:
            pass

    current_container = client.containers.run(
        "python:3.12-slim",
        command="sleep infinity",
        detach=True,
        working_dir=WORKSPACE_DIR,
        auto_remove=True
    )
    current_container.exec_run(f"mkdir -p {WORKSPACE_DIR}")
    return current_container

def execute_command(command: str) -> str:
    container = get_or_create_container()
    exit_code, output = container.exec_run(
        ['/bin/bash', '-c', command],
        workdir=WORKSPACE_DIR
    )
    res = output.decode('utf-8')
    if exit_code != 0:
        return f"Error (Exit Code {exit_code}):\n{res}"
    return res

def apply_patch(file_path: str, patch_content: str) -> str:
    container = get_or_create_container()
    b64_content = base64.b64encode(patch_content.encode('utf-8')).decode('utf-8')
    # Using base64 to avoid quoting nightmares in bash
    cmd = f"echo {b64_content} | base64 -d > {file_path}"
    return execute_command(cmd)

def reset_sandbox() -> str:
    global current_container
    if current_container:
        try:
            current_container.stop(timeout=1)
        except Exception:
            pass
        current_container = None
    return "Sandbox reset successfully. A new container will be created on the next command."
