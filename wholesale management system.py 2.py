import json
from datetime import datetime, timedelta
import random
import string
import hashlib
import sqlite3  # Using SQLite instead of JSON for better reliability

class WholesaleManagementSystem:
    def __init__(self):
        self.conn = sqlite3.connect('wholesale.db')
        self.cursor = self.conn.cursor()
        self._init_db()
        self.current_user = None

    def _init_db(self):
        """Initialize database tables"""
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS products (
                            id TEXT PRIMARY KEY,
                            name TEXT,
                            description TEXT,
                            cost_price REAL,
                            selling_price REAL,
                            barcode TEXT,
                            category TEXT)''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS customers (
                            id TEXT PRIMARY KEY,
                            name TEXT,
                            address TEXT,
                            phone TEXT,
                            email TEXT,
                            discount_rate REAL)''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
                            product_id TEXT,
                            location TEXT,
                            quantity INTEGER,
                            PRIMARY KEY (product_id, location))''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            username TEXT PRIMARY KEY,
                            password_hash TEXT,
                            role TEXT)''')
        
        # Add default admin user if not exists
        self.cursor.execute("SELECT * FROM users WHERE username='admin'")
        if not self.cursor.fetchone():
            self._add_user('admin', 'admin123', 'admin')
        
        self.conn.commit()

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def _add_user(self, username, password, role='staff'):
        """Internal method to add users"""
        try:
            self.cursor.execute("INSERT INTO users VALUES (?, ?, ?)",
                              (username, self._hash_password(password), role))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login(self, username, password):
        """Authenticate users"""
        self.cursor.execute("SELECT password_hash FROM users WHERE username=?", (username,))
        result = self.cursor.fetchone()
        if result and result[0] == self._hash_password(password):
            self.current_user = username
            return True
        return False

    def add_product(self, product_id, name, description, cost_price, selling_price, category='General'):
        """Add a new product to inventory"""
        try:
            self.cursor.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (product_id, name, description, cost_price, selling_price, 
                               ''.join(random.choices(string.digits, k=12)), category))
            # Initialize inventory
            self.cursor.execute("INSERT INTO inventory VALUES (?, ?, ?)",
                              (product_id, 'main_warehouse', 0))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_inventory(self, product_id, location, quantity_change):
        """Update inventory levels"""
        self.cursor.execute('''INSERT OR IGNORE INTO inventory VALUES (?, ?, 0)''',
                          (product_id, location))
        self.cursor.execute('''UPDATE inventory SET quantity = quantity + ? 
                            WHERE product_id=? AND location=?''',
                          (quantity_change, product_id, location))
        self.conn.commit()

    def create_sale(self, customer_id, items, location='main_warehouse'):
        """Process a new sale"""
        # Verify all items are available
        for product_id, quantity in items.items():
            self.cursor.execute('''SELECT quantity FROM inventory 
                                WHERE product_id=? AND location=?''',
                              (product_id, location))
            result = self.cursor.fetchone()
            if not result or result[0] < quantity:
                return False, f"Insufficient stock for product {product_id}"
        
        # Process the sale
        total = 0
        for product_id, quantity in items.items():
            # Get product price
            self.cursor.execute('''SELECT selling_price FROM products WHERE id=?''',
                              (product_id,))
            price = self.cursor.fetchone()[0]
            total += price * quantity
            
            # Update inventory
            self.update_inventory(product_id, location, -quantity)
        
        # Record the sale (simplified)
        sale_id = f"SALE-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        return True, f"Sale {sale_id} processed. Total: ${total:.2f}"

    def generate_inventory_report(self):
        """Generate inventory report"""
        self.cursor.execute('''SELECT p.name, i.location, i.quantity, p.selling_price
                            FROM inventory i JOIN products p ON i.product_id = p.id
                            ORDER BY p.name, i.location''')
        return self.cursor.fetchall()

    def menu(self):
        """Main menu interface"""
        while True:
            print("\n=== Wholesale Management System ===")
            print("1. Add Product")
            print("2. Update Inventory")
            print("3. Process Sale")
            print("4. View Inventory Report")
            print("5. Exit")
            
            choice = input("Enter your choice (1-5): ")
            
            if choice == '1':
                product_id = input("Enter product ID: ")
                name = input("Enter product name: ")
                description = input("Enter product description: ")
                cost = float(input("Enter cost price: "))
                price = float(input("Enter selling price: "))
                if self.add_product(product_id, name, description, cost, price):
                    print("Product added successfully!")
                else:
                    print("Error: Product ID already exists!")
            
            elif choice == '2':
                product_id = input("Enter product ID: ")
                location = input("Enter location (default: main_warehouse): ") or 'main_warehouse'
                quantity = int(input("Enter quantity change (+/-): "))
                self.update_inventory(product_id, location, quantity)
                print("Inventory updated!")
            
            elif choice == '3':
                customer_id = input("Enter customer ID: ")
                items = {}
                while True:
                    product_id = input("Enter product ID (or 'done'): ")
                    if product_id.lower() == 'done':
                        break
                    quantity = int(input("Enter quantity: "))
                    items[product_id] = quantity
                success, message = self.create_sale(customer_id, items)
                print(message)
            
            elif choice == '4':
                print("\n=== Inventory Report ===")
                print("{:<20} {:<15} {:<10} {:<10}".format(
                    "Product", "Location", "Quantity", "Unit Price"))
                for item in self.generate_inventory_report():
                    print("{:<20} {:<15} {:<10} ${:<9.2f}".format(*item))
            
            elif choice == '5':
                print("Goodbye!")
                break
            
            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    system = WholesaleManagementSystem()
    
    # Simple login
    print("=== Wholesale Management System Login ===")
    username = input("Username: ")
    password = input("Password: ")
    
    if system.login(username, password):
        system.menu()
    else:
        print("Invalid credentials!")