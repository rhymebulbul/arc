import os
from mcp_ast_server.tools import get_function_signature, get_class_methods, extract_code_block

# Get the path to dummy_code.py relative to this test file
DUMMY_CODE_PATH = os.path.join(os.path.dirname(__file__), 'dummy_code.py')

def test_get_function_signature_exists():
    sig = get_function_signature(DUMMY_CODE_PATH, 'calculate_tax')
    assert sig.strip() == 'def calculate_tax(amount: float) -> float:'

def test_get_function_signature_not_exists():
    res = get_function_signature(DUMMY_CODE_PATH, 'non_existent')
    assert res.startswith('Error:')

def test_get_class_methods_exists():
    methods = get_class_methods(DUMMY_CODE_PATH, 'PaymentGateway')
    assert len(methods) == 2
    assert methods[0] == 'def process_payment(self, amount: float, currency: str) -> bool:'
    assert methods[1] == 'def refund_payment(self, transaction_id: str) -> bool:'

def test_get_class_methods_not_exists():
    res = get_class_methods(DUMMY_CODE_PATH, 'NonExistentClass')
    assert len(res) == 1
    assert res[0].startswith('Error:')

def test_extract_code_block():
    block = extract_code_block(DUMMY_CODE_PATH, 1, 1)
    assert block.strip() == 'class PaymentGateway:'

def test_extract_code_block_invalid():
    res = extract_code_block(DUMMY_CODE_PATH, 100, 110)
    assert res.startswith('Error:')
