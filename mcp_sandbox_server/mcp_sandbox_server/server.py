from fastmcp import FastMCP
from .tools import execute_command, apply_patch, reset_sandbox

mcp = FastMCP("arc-sandbox-server")

@mcp.tool()
def command_runner(command: str) -> str:
    """Runs a shell command inside the ephemeral Docker container.
    Returns stdout. If the command fails, returns stderr and the exit code.
    """
    return execute_command(command)

@mcp.tool()
def patch_file(file_path: str, patch_content: str) -> str:
    """Overwrites or creates a file at file_path inside the container with patch_content.
    Use this to apply your proposed code changes.
    """
    return apply_patch(file_path, patch_content)

@mcp.tool()
def reset_environment() -> str:
    """Destroys the current container and provisions a fresh one.
    Use this if you have completely broken the repository state and need a clean slate.
    """
    return reset_sandbox()

if __name__ == "__main__":
    mcp.run()
