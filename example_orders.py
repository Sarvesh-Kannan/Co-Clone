"""
Example orders module for demonstrating function change tracking
"""

from example_utils import calculate_total, format_money, validate_input

def create_order(product_name, price, quantity, customer_discount=0):
    """Create an order with the given parameters"""
    validate_input(quantity, min_value=1)
    validate_input(price, min_value=0.01)
    
    total = calculate_total(price, quantity, discount=customer_discount)
    
    return {
        "product": product_name,
        "price_per_unit": price,
        "quantity": quantity,
        "discount": customer_discount,
        "total": total,
        "formatted_total": format_money(total)
    }

def bulk_order_discount(order_count):
    """Calculate bulk order discount based on order count"""
    if order_count >= 10:
        return 0.15  # 15% discount for 10+ orders
    elif order_count >= 5:
        return 0.10  # 10% discount for 5-9 orders
    elif order_count >= 3:
        return 0.05  # 5% discount for 3-4 orders
    return 0  # No discount for 1-2 orders

def print_order_summary(order):
    """Print a summary of the order"""
    print(f"Order Summary:")
    print(f"Product: {order['product']}")
    print(f"Quantity: {order['quantity']} @ {format_money(order['price_per_unit'])} each")
    if order['discount'] > 0:
        print(f"Discount: {order['discount'] * 100:.0f}%")
    print(f"Total: {order['formatted_total']}")

# Example usage
if __name__ == "__main__":
    # Create a sample order
    sample_order = create_order(
        product_name="Widget Pro",
        price=29.99,
        quantity=3,
        customer_discount=0.05
    )
    
    # Print the order summary
    print_order_summary(sample_order) 