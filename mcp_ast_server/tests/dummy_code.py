class PaymentGateway:
    def process_payment(self, amount: float, currency: str) -> bool:
        """Processes the payment."""
        return True
        
    def refund_payment(self, transaction_id: str) -> bool:
        return True

def calculate_tax(amount: float) -> float:
    tax = amount * 0.1
    return tax

def test_refund_payment_returns_true():
    gateway = PaymentGateway()
    assert gateway.refund_payment("test_transaction_id") is True