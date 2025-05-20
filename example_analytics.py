"""
Example analytics module for demonstrating function change tracking
"""

from example_utils import calculate_total, format_money, validate_input

def calculate_revenue(sales_data):
    """Calculate total revenue from sales data"""
    total_revenue = 0
    
    for sale in sales_data:
        # Validate the input data
        validate_input(sale.get("price", 0), min_value=0.01)
        validate_input(sale.get("quantity", 0), min_value=1)
        
        # Calculate the revenue for this sale
        sale_revenue = calculate_total(
            sale["price"], 
            sale["quantity"],
            discount=sale.get("discount", 0)
        )
        
        total_revenue += sale_revenue
    
    return {
        "total_revenue": total_revenue,
        "formatted_revenue": format_money(total_revenue),
        "sales_count": len(sales_data)
    }

def calculate_average_order_value(sales_data):
    """Calculate the average order value"""
    revenue_data = calculate_revenue(sales_data)
    
    if revenue_data["sales_count"] > 0:
        average = revenue_data["total_revenue"] / revenue_data["sales_count"]
        return {
            "average_order": average,
            "formatted_average": format_money(average),
            "total_orders": revenue_data["sales_count"]
        }
    
    return {
        "average_order": 0,
        "formatted_average": format_money(0),
        "total_orders": 0
    }

def print_sales_analysis(sales_data):
    """Print a sales analysis report"""
    revenue_data = calculate_revenue(sales_data)
    average_data = calculate_average_order_value(sales_data)
    
    print("\nSales Analysis Report")
    print("-" * 40)
    print(f"Total Sales Count: {revenue_data['sales_count']}")
    print(f"Total Revenue: {revenue_data['formatted_revenue']}")
    print(f"Average Order Value: {average_data['formatted_average']}")
    
    # Product breakdown
    product_sales = {}
    for sale in sales_data:
        product = sale["product"]
        if product not in product_sales:
            product_sales[product] = {
                "quantity": 0,
                "revenue": 0
            }
        
        # Calculate this sale's revenue
        sale_revenue = calculate_total(
            sale["price"], 
            sale["quantity"],
            discount=sale.get("discount", 0)
        )
        
        product_sales[product]["quantity"] += sale["quantity"]
        product_sales[product]["revenue"] += sale_revenue
    
    # Print product breakdown
    print("\nProduct Breakdown:")
    for product, data in product_sales.items():
        print(f"  {product}: {data['quantity']} units, {format_money(data['revenue'])}")

# Example usage
if __name__ == "__main__":
    # Sample sales data
    sales = [
        {"product": "Widget Pro", "price": 29.99, "quantity": 5, "discount": 0},
        {"product": "Widget Pro", "price": 29.99, "quantity": 10, "discount": 0.1},
        {"product": "Gadget Basic", "price": 19.99, "quantity": 15, "discount": 0},
        {"product": "Super Tool", "price": 49.99, "quantity": 2, "discount": 0},
        {"product": "Budget Item", "price": 9.99, "quantity": 20, "discount": 0.05}
    ]
    
    # Print sales analysis
    print_sales_analysis(sales) 