"""
Example utilities module for demonstrating function change tracking
"""

def calculate_totals(base_amount, quantity, discount=0, tax_rate=0.0):
    """Calculate the total amount with optional discount and tax"""
    subtotal = base_amount * quantity
    discounted_total = subtotal * (1 - discount)
    return discounted_total * (1 + tax_rate)

def format_money(amount):
    """Format a number as currency"""
    return f"${amount:.2f}"

def validate_input(value, min_value=0):
    """Validate that a value is at least the minimum value"""
    if value < min_value:
        raise ValueError(f"Value must be at least {min_value}")
    return True 