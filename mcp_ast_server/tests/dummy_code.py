class PaymentGateway:
    def process_payment(self, amount: float, currency: str) -> bool:
        """Processes the payment."""
        return True
        
    def refund_payment(self, transaction_id: str) -> bool:
        return False

def calculate_tax(amount: float) -> float:
    tax = amount * 0.1
    return tax
