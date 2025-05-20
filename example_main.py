"""
Main example file to demonstrate function change tracking across multiple files
"""

from example_utils import calculate_total, format_money, validate_input
from example_orders import create_order, bulk_order_discount, print_order_summary
from example_inventory import calculate_inventory_value, check_reorder, print_inventory_report
from example_analytics import calculate_revenue, calculate_average_order_value, print_sales_analysis

def run_examples():
    """Run examples from all modules to demonstrate function usage"""
    print("=" * 50)
    print("FUNCTION CHANGE TRACKING DEMONSTRATION")
    print("=" * 50)
    
    # Create and display an order
    print("\n1. Creating and displaying an order:")
    print("-" * 40)
    
    # Calculate discount based on order count
    order_count = 6
    discount = bulk_order_discount(order_count)
    print(f"Bulk order discount for {order_count} orders: {discount * 100:.0f}%")
    
    # Create the order
    order = create_order(
        product_name="Premium Widget",
        price=49.99,
        quantity=order_count,
        customer_discount=discount
    )
    
    # Print the order summary
    print_order_summary(order)
    
    # Display inventory information
    print("\n2. Inventory management:")
    print("-" * 40)
    
    # Sample inventory
    inventory = [
        {"name": "Premium Widget", "price": 49.99, "quantity": 15},
        {"name": "Standard Widget", "price": 29.99, "quantity": 8},
        {"name": "Budget Widget", "price": 19.99, "quantity": 5},
        {"name": "Luxury Gadget", "price": 99.99, "quantity": 2}
    ]
    
    # Print inventory report
    print_inventory_report(inventory)
    
    # Sales analysis
    print("\n3. Sales Analysis:")
    print("-" * 40)
    
    # Sample sales data
    sales = [
        {"product": "Premium Widget", "price": 49.99, "quantity": 5, "discount": 0},
        {"product": "Premium Widget", "price": 49.99, "quantity": 10, "discount": 0.1},
        {"product": "Standard Widget", "price": 29.99, "quantity": 15, "discount": 0},
        {"product": "Budget Widget", "price": 19.99, "quantity": 20, "discount": 0},
        {"product": "Luxury Gadget", "price": 99.99, "quantity": 3, "discount": 0.05}
    ]
    
    # Print sales analysis
    print_sales_analysis(sales)
    
    # Direct demonstration of the utility functions
    print("\n4. Direct Usage of Utility Functions:")
    print("-" * 40)
    
    # Calculate total
    amount = 59.99
    qty = 3
    disc = 0.1
    total = calculate_total(amount, qty, discount=disc)
    print(f"Calculated total: {amount} x {qty} with {disc*100:.0f}% discount = {format_money(total)}")
    
    # Validate input
    try:
        print("Validating valid input (5): ", validate_input(5, min_value=1))
        print("Validating invalid input (-5): ", end="")
        validate_input(-5, min_value=1)
    except ValueError as e:
        print(f"Error caught: {e}")
    
    print("\nDemonstration completed!")
    print("=" * 50)
    print("Now you can modify the calculate_total function in example_utils.py")
    print("to add a new parameter and see how the change is detected")
    print("in all the files that use this function.")
    print("=" * 50)

if __name__ == "__main__":
    run_examples() 