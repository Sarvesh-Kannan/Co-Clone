"""
Example inventory module for demonstrating function change tracking
"""

from example_utils import calculate_total, format_money, validate_input

def calculate_inventory_value(item_price, quantity_in_stock):
    """Calculate the total value of inventory for an item"""
    validate_input(quantity_in_stock)
    validate_input(item_price, min_value=0.01)
    
    # Calculate the total value using the utility function
    total_value = calculate_total(item_price, quantity_in_stock)
    
    return {
        "quantity": quantity_in_stock,
        "unit_price": item_price,
        "total_value": total_value,
        "formatted_value": format_money(total_value)
    }

def check_reorder(product_name, current_stock, reorder_level=10):
    """Check if a product needs to be reordered"""
    validate_input(current_stock)
    validate_input(reorder_level, min_value=1)
    
    if current_stock <= reorder_level:
        return {
            "product": product_name,
            "current_stock": current_stock,
            "reorder_level": reorder_level,
            "needs_reorder": True,
            "message": f"REORDER NEEDED: {product_name} (Stock: {current_stock}, Threshold: {reorder_level})"
        }
    else:
        return {
            "product": product_name,
            "current_stock": current_stock,
            "reorder_level": reorder_level,
            "needs_reorder": False,
            "message": f"Stock OK: {product_name} (Stock: {current_stock}, Threshold: {reorder_level})"
        }

def print_inventory_report(items):
    """Print a report of inventory items"""
    total_inventory_value = 0
    
    print("\nInventory Report")
    print("-" * 40)
    print(f"{'Product':<20} {'Stock':<8} {'Value':<12}")
    print("-" * 40)
    
    for item in items:
        inventory_value = calculate_inventory_value(
            item["price"], 
            item["quantity"]
        )
        total_inventory_value += inventory_value["total_value"]
        
        print(f"{item['name']:<20} {item['quantity']:<8} {inventory_value['formatted_value']:<12}")
        
        # Check if reorder is needed
        reorder_status = check_reorder(item["name"], item["quantity"])
        if reorder_status["needs_reorder"]:
            print(f"  * {reorder_status['message']}")
    
    print("-" * 40)
    print(f"Total Inventory Value: {format_money(total_inventory_value)}")

# Example usage
if __name__ == "__main__":
    # Sample inventory
    inventory = [
        {"name": "Widget Pro", "price": 29.99, "quantity": 15},
        {"name": "Gadget Basic", "price": 19.99, "quantity": 8},
        {"name": "Super Tool", "price": 49.99, "quantity": 5},
        {"name": "Budget Item", "price": 9.99, "quantity": 25}
    ]
    
    # Print inventory report
    print_inventory_report(inventory) 