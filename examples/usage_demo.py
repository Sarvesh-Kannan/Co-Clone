"""
Demo file specifically created to show function tracking
"""

from example_utils import calculate_total, format_money

def show_price_calculation():
    """Demonstrate using the calculate_total function with different parameters"""
    product_price = 49.99
    quantity = 3
    discount = 0.1  # 10% discount
    
    # Use the basic version without tax
    subtotal = calculate_total(product_price, quantity, discount)
    
    print(f"Product: Premium Widget")
    print(f"Price: {format_money(product_price)} each")
    print(f"Quantity: {quantity}")
    print(f"Discount: {discount * 100:.0f}%")
    print(f"Subtotal (no tax): {format_money(subtotal)}")
    
    # This function call should be detected by the system as needing an update
    # to include the new tax_rate parameter

if __name__ == "__main__":
    show_price_calculation()
    print("\nFunction tracking should detect that this file needs to update its call to calculate_total")