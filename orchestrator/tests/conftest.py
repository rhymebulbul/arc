"""Shared fixtures and test helpers for Orchestrator E2E Acceptance Suite."""

import os
import sys
import pytest
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure repo root and orchestrator are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ORCHESTRATOR_ROOT = REPO_ROOT / "orchestrator"
AST_SERVER_ROOT = REPO_ROOT / "mcp_ast_server"
SANDBOX_SERVER_ROOT = REPO_ROOT / "mcp_sandbox_server"

for path in [str(REPO_ROOT), str(ORCHESTRATOR_ROOT), str(AST_SERVER_ROOT), str(SANDBOX_SERVER_ROOT)]:
    if path not in sys.path:
        sys.path.insert(0, path)

DUMMY_CODE_PATH = AST_SERVER_ROOT / "tests" / "dummy_code.py"


@pytest.fixture
def repo_root_path() -> Path:
    """Returns the absolute repository root path."""
    return REPO_ROOT


@pytest.fixture
def dummy_code_file_path() -> str:
    """Returns the absolute path to dummy_code.py."""
    return str(DUMMY_CODE_PATH)


@pytest.fixture
def original_dummy_code() -> str:
    """Returns the original content of dummy_code.py with deliberate bug."""
    if DUMMY_CODE_PATH.exists():
        return DUMMY_CODE_PATH.read_text(encoding="utf-8")
    return '''class PaymentGateway:
    def process_payment(self, amount: float, currency: str) -> bool:
        """Processes the payment."""
        return True
        
    def refund_payment(self, transaction_id: str) -> bool:
        return False

def calculate_tax(amount: float) -> float:
    tax = amount * 0.1
    return tax
'''


@pytest.fixture
def fixed_dummy_code() -> str:
    """Returns the expected corrected content of dummy_code.py."""
    return '''class PaymentGateway:
    def process_payment(self, amount: float, currency: str) -> bool:
        """Processes the payment."""
        return True
        
    def refund_payment(self, transaction_id: str) -> bool:
        return True

def calculate_tax(amount: float) -> float:
    tax = amount * 0.1
    return tax
'''


@pytest.fixture
def isolated_dummy_file(tmp_path, original_dummy_code) -> str:
    """Creates an isolated temporary copy of dummy_code.py for safe testing."""
    test_file = tmp_path / "dummy_code.py"
    test_file.write_text(original_dummy_code, encoding="utf-8")
    return str(test_file)
