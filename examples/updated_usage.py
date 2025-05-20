"""
Demo file showing the correct updated usage with tax_rate parameter
"""

from example_utils import calculate_total, format_money

def show_complete_price_calculation():
    """Demonstrate using the calculate_total function with all parameters including tax_rate"""
    product_price = 49.99
    quantity = 3
    discount = 0.1  # 10% discount
    tax_rate = 0.08  # 8% tax
    
    # Use the full version with tax rate
    total = calculate_total(product_price, quantity, discount, tax_rate)
    
    print(f"Product: Premium Widget")
    print(f"Price: {format_money(product_price)} each")
    print(f"Quantity: {quantity}")
    print(f"Discount: {discount * 100:.0f}%")
    print(f"Tax Rate: {tax_rate * 100:.0f}%")
    print(f"Total (with tax): {format_money(total)}")
    
    # This function correctly uses all parameters including tax_rate

if __name__ == "__main__":
    show_complete_price_calculation()
    print("\nThis file correctly uses the calculate_total function with all parameters")