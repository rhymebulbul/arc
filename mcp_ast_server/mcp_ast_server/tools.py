import os
from .parser import parse_file

def _get_node_text(node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode('utf8')

def get_function_signature(file_path: str, function_name: str) -> str:
    """Extracts the exact string of a function signature from a file."""
    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' does not exist."
    
    try:
        tree, src = parse_file(file_path)
    except Exception as e:
        return f"Error: Failed to parse file: {str(e)}"
    
    root_node = tree.root_node
    
    def find_function(node, name):
        if node.type == 'function_definition':
            name_node = node.child_by_field_name('name')
            if name_node and _get_node_text(name_node, src) == name:
                return node
        
        for child in node.children:
            res = find_function(child, name)
            if res: return res
        return None

    func_node = find_function(root_node, function_name)
    if not func_node:
        return f"Error: Function '{function_name}' not found in '{file_path}'."
    
    node_text = _get_node_text(func_node, src)
    signature = node_text.split(":\n")[0] + ":"
    return signature

def get_class_methods(file_path: str, class_name: str) -> list[str]:
    """Returns a list of method signatures belonging to the specified class."""
    if not os.path.exists(file_path):
        return [f"Error: File '{file_path}' does not exist."]
    
    try:
        tree, src = parse_file(file_path)
    except Exception as e:
        return [f"Error: Failed to parse file: {str(e)}"]
        
    root_node = tree.root_node
    
    def find_class(node, name):
        if node.type == 'class_definition':
            name_node = node.child_by_field_name('name')
            if name_node and _get_node_text(name_node, src) == name:
                return node
        
        for child in node.children:
            res = find_class(child, name)
            if res: return res
        return None

    class_node = find_class(root_node, class_name)
    if not class_node:
        return [f"Error: Class '{class_name}' not found in '{file_path}'."]
    
    methods = []
    body_node = class_node.child_by_field_name('body')
    if body_node:
        for child in body_node.children:
            if child.type == 'function_definition':
                node_text = _get_node_text(child, src)
                sig = node_text.split(":\n")[0] + ":"
                methods.append(sig.strip())
                
    return methods

def extract_code_block(file_path: str, start_line: int, end_line: int) -> str:
    """Reads a specific block of code based on line numbers (1-indexed)."""
    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' does not exist."
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    if start_line < 1 or end_line > len(lines) or start_line > end_line:
        return f"Error: Invalid line range {start_line}-{end_line} for file of length {len(lines)}."
        
    return "".join(lines[start_line-1:end_line])
