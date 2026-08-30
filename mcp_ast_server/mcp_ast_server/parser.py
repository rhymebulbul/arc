import tree_sitter_python as tspython
from tree_sitter import Language, Parser

def get_parser() -> Parser:
    PY_LANGUAGE = Language(tspython.language())
    parser = Parser(PY_LANGUAGE)
    return parser

def parse_file(file_path: str):
    with open(file_path, 'rb') as f:
        src = f.read()
    parser = get_parser()
    tree = parser.parse(src)
    return tree, src
