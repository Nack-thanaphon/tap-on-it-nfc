import time
import json
import os
from datetime import datetime

class APIService:
    """Simulates API calls to an external service."""
    
    def __init__(self):
        """Initialize the API service with sample data."""
        self.data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_data.json")
        self.load_data()
    
    def load_data(self):
        """Load data from file or create sample data if file doesn't exist."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.orders = json.load(f)
            except:
                self.orders = self.create_sample_data()
                self.save_data()
        else:
            self.orders = self.create_sample_data()
            self.save_data()
    
    def save_data(self):
        """Save data to file to simulate persistence."""
        with open(self.data_file, 'w') as f:
            json.dump(self.orders, f, indent=2)
    
    def create_sample_data(self):
        """Create sample order data."""
        today = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return [
            {
                "id": 1,
                "order_number": "ORD-001",
                "customer_name": "John Doe",
                "title": "Premium Coffee Beans",
                "url": "https://example.com/product/coffee",
                "tag_color": "#FF5733",
                "status": "Pending",
                "date": today,
                "created_at": timestamp,
                "updated_at": timestamp
            },
            {
                "id": 2,
                "order_number": "ORD-002",
                "customer_name": "Jane Smith",
                "title": "Organic Tea Set",
                "url": "https://store.com/inventory/tea",
                "tag_color": "#33FF57",
                "status": "Pending",
                "date": today,
                "created_at": timestamp,
                "updated_at": timestamp
            },
            {
                "id": 3,
                "order_number": "ORD-003",
                "customer_name": "Bob Johnson",
                "title": "Specialty Chocolate",
                "url": "https://loyalty.com/reward/chocolate",
                "tag_color": "#3357FF",
                "status": "Pending",
                "date": today,
                "created_at": timestamp,
                "updated_at": timestamp
            },
            {
                "id": 4,
                "order_number": "ORD-004",
                "customer_name": "Alice Brown",
                "title": "Gift Card",
                "url": "https://example.com/giftcard",
                "tag_color": "#FF33A1",
                "status": "Completed",
                "date": today,
                "created_at": timestamp,
                "updated_at": timestamp
            }
        ]
    
    def get_orders(self, date=None, status=None, search_term=None):
        """Simulate API call to get orders with filtering."""
        # Simulate network delay
        time.sleep(0.2)
        
        # Apply filters
        filtered_orders = self.orders.copy()
        
        if date:
            filtered_orders = [order for order in filtered_orders if order["date"] == date]
        
        if status:
            filtered_orders = [order for order in filtered_orders if order["status"] == status]
        
        if search_term:
            search_term = search_term.lower()
            filtered_orders = [
                order for order in filtered_orders 
                if (search_term in order["order_number"].lower() or
                    search_term in order["customer_name"].lower() or
                    search_term in order["title"].lower())
            ]
        
        # Sort by date and ID
        filtered_orders.sort(key=lambda x: (x["date"], x["id"]), reverse=True)
        
        return filtered_orders
    
    def update_order_status(self, order_id, status):
        """Simulate API call to update order status."""
        # Simulate network delay
        time.sleep(0.3)
        
        for order in self.orders:
            if order["id"] == order_id:
                order["status"] = status
                order["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.save_data()
                return True
        
        return False
    
    def add_order(self, order_number, customer_name, product_name, url, tag_color="#FF5733", status="Pending"):
        """Simulate API call to add a new order."""
        # Simulate network delay
        time.sleep(0.5)
        
        today = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Generate new ID
        new_id = max([order["id"] for order in self.orders]) + 1 if self.orders else 1
        
        new_order = {
            "id": new_id,
            "order_number": order_number,
            "customer_name": customer_name,
            "title": product_name,
            "url": url,
            "tag_color": tag_color,
            "status": status,
            "date": today,
            "created_at": timestamp,
            "updated_at": timestamp
        }
        
        self.orders.append(new_order)
        self.save_data()
        
        return new_id
