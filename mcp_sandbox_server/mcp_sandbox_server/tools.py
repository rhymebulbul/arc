from .sandbox import execute_command as _execute_command, apply_patch as _apply_patch, reset_sandbox as _reset_sandbox

def execute_command(command: str) -> str:
    return _execute_command(command)

def apply_patch(file_path: str, patch_content: str) -> str:
    return _apply_patch(file_path, patch_content)

def reset_sandbox() -> str:
    return _reset_sandbox()
