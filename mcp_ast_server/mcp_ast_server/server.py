from fastmcp import FastMCP
from .tools import get_function_signature, get_class_methods, extract_code_block

# Initialize the FastMCP server
mcp = FastMCP("arc-ast-server")

@mcp.tool()
def function_signature(file_path: str, function_name: str) -> str:
    """Extracts the exact string of a function signature from a file.
    Use this to understand a function's parameters and return types without reading the whole body.
    """
    return get_function_signature(file_path, function_name)

@mcp.tool()
def class_methods(file_path: str, class_name: str) -> list[str]:
    """Returns a list of method signatures belonging to the specified class.
    Use this to understand the interface of a class.
    """
    return get_class_methods(file_path, class_name)

@mcp.tool()
def extract_block(file_path: str, start_line: int, end_line: int) -> str:
    """Reads a specific block of code based on 1-indexed line numbers.
    Use this if you know the exact lines from a compiler error trace.
    """
    return extract_code_block(file_path, start_line, end_line)

if __name__ == "__main__":
    mcp.run(show_banner=False)
