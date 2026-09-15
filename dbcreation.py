# dbcreation.py
import sqlite3
import random
import time
import bcrypt

# Database file
db_name = "shopfleet.db"

# Connect
conn = sqlite3.connect(db_name)
cursor = conn.cursor()

# Utility: hash password
def hash_password(plain_text_password: str) -> str:
    return bcrypt.hashpw(plain_text_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# ID base offsets (your existing system)
BASE_USER = 100_000_000
BASE_EMPLOYEE = 200_000_000
BASE_PRODUCT = 300_000_000
BASE_FLEET = 400_000_000
BASE_ORDER = 500_000_000
BASE_REVIEW = 600_000_000
BASE_CART = 700_000_000
BASE_GAS_REFILL = 800_000_000  # 🔥 NEW: Gas Refill Orders
BASE_FLEET_ORDERS = 900_000_000 # NEW: Fleet Orders
BASE_FLEET_ASSIGNMENTS = 1_000_000_000 # NEW: Fleet Order Assignments
BASE_BULK_ORDERS = 1_100_000_000  # NEW: Bulk Orders

# -------------------------------
# Create Tables (if not exist) - Using original structure
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS `Users` (
    `user_id` INTEGER PRIMARY KEY NOT NULL UNIQUE,
    `first_name` TEXT NOT NULL,
    `last_name` TEXT NOT NULL,
    `phone_number` INTEGER NOT NULL,
    `email` TEXT NOT NULL UNIQUE,
    `password` TEXT NOT NULL,
    `otp` TEXT,
    `otp_timestamp` REAL,
    `location` TEXT NOT NULL, -- This is the user's general location, not ping location
    `status` TEXT NOT NULL DEFAULT 'Inactive',
    `last_login` REAL NOT NULL
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS `Employees` (
    `employee_id` INTEGER PRIMARY KEY NOT NULL UNIQUE,
    `first_name` TEXT NOT NULL,
    `last_name` TEXT NOT NULL,
    `phone_number` INTEGER NOT NULL,
    `email` TEXT NOT NULL UNIQUE,
    `password` TEXT NOT NULL,
    `otp` TEXT NOT NULL,
    `otp_timestamp` REAL NOT NULL,
    `location` TEXT NOT NULL, -- This is the employee's general location, not ping location
    `role` TEXT NOT NULL DEFAULT 'Customer',
    `status` TEXT NOT NULL DEFAULT 'Inactive',
    `last_login` REAL NOT NULL
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS `Products` (
    `product_id` INTEGER PRIMARY KEY NOT NULL UNIQUE,
    `product_name` TEXT NOT NULL,
    `product_category` TEXT NOT NULL,
    `product_description` TEXT NOT NULL,
    `product_image` TEXT NOT NULL,
    `product_quantity` INTEGER NOT NULL,
    `product_cost` INTEGER NOT NULL,
    `retail_price` INTEGER NOT NULL,
    `employee_id` INTEGER,  -- Changed from user_id to employee_id
    `product_registration` TEXT NOT NULL,
    `product_location` TEXT NOT NULL,
    `location_description` TEXT,
    `status` TEXT NOT NULL DEFAULT 'Not sold',
    FOREIGN KEY(`employee_id`) REFERENCES `Employees`(`employee_id`)  -- Updated foreign key
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS `Cart` (
    `cart_id` INTEGER PRIMARY KEY NOT NULL UNIQUE,
    `product_id` INTEGER NOT NULL,
    `user_id` INTEGER,
    `status` TEXT NOT NULL DEFAULT 'Wishlist',
    FOREIGN KEY(`product_id`) REFERENCES `Products`(`product_id`),
    FOREIGN KEY(`user_id`) REFERENCES `Users`(`user_id`)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS `Orders` (
    `order_id` INTEGER PRIMARY KEY NOT NULL UNIQUE,
    `cart_id` INTEGER NOT NULL,
    `employee_id` INTEGER NOT NULL,
    `fleet_id` INTEGER NOT NULL,
    `status` TEXT NOT NULL DEFAULT 'Stage 1',
    `product_destination` TEXT,
    `product_arrival` REAL NOT NULL DEFAULT 'False',
    `otp` TEXT NOT NULL DEFAULT 'No OTP',
    `otp_timestamp` REAL NOT NULL DEFAULT '0',
    `order_timestamp` REAL NOT NULL,
    FOREIGN KEY(`cart_id`) REFERENCES `Cart`(`cart_id`),
    FOREIGN KEY(`employee_id`) REFERENCES `Employees`(`employee_id`),
    FOREIGN KEY(`fleet_id`) REFERENCES `Fleet`(`fleet_id`)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS `Fleet` (
    `fleet_id` INTEGER PRIMARY KEY NOT NULL UNIQUE,
    `registration_number` TEXT NOT NULL UNIQUE,
    `fleet_brand` TEXT NOT NULL,
    `fleet_model` TEXT NOT NULL,
    `fleet_category` TEXT NOT NULL,
    `registration_date` REAL NOT NULL,
    `employee_id` INTEGER NOT NULL,
    `fleet_mileage` INTEGER NOT NULL,
    `chassis_number` INTEGER NOT NULL,
    `cargo_type` TEXT NOT NULL,
    `max_capacity` INTEGER NOT NULL,
    `status` TEXT NOT NULL DEFAULT 'Inactive',
    `last_login` REAL NOT NULL,
    FOREIGN KEY(`employee_id`) REFERENCES `Employees`(`employee_id`)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS `Reviews` (
    `review_id` INTEGER PRIMARY KEY NOT NULL UNIQUE,
    `product_id` INTEGER NOT NULL,
    `text_review` TEXT NOT NULL,
    `ratings` INTEGER NOT NULL,
    `user_id` INTEGER NOT NULL,
    `review_timestamp` TEXT NOT NULL,
    `status` TEXT NOT NULL DEFAULT 'Not sold',
    FOREIGN KEY(`product_id`) REFERENCES `Products`(`product_id`),
    FOREIGN KEY(`user_id`) REFERENCES `Users`(`user_id`)
);
""")

# 🔥 NEW TABLE: GasRefillOrders - Using original structure
cursor.execute("""
CREATE TABLE IF NOT EXISTS `GasRefillOrders` (
    `order_id` INTEGER PRIMARY KEY NOT NULL UNIQUE, -- Changed from AUTOINCREMENT to UNIQUE
    `user_id` INTEGER NOT NULL,
    `cylinder_type` TEXT NOT NULL,
    `size_kg` TEXT NOT NULL,
    `location` TEXT NOT NULL,
    `instructions` TEXT,
    `status` TEXT DEFAULT 'Pending',
    `order_timestamp` REAL NOT NULL,
    FOREIGN KEY(`user_id`) REFERENCES `Users`(`user_id`)
);
""")

# NEW TABLE: FleetOrders - Track quantity requested with duration
cursor.execute("""
CREATE TABLE IF NOT EXISTS `FleetOrders` (
    `fleetorder_id` INTEGER PRIMARY KEY NOT NULL UNIQUE,
    `user_id` INTEGER NOT NULL,
    `cargo_type` TEXT NOT NULL,
    `quantity` INTEGER NOT NULL, -- Number of vehicles requested
    `assigned_quantity` INTEGER DEFAULT 0, -- Number of vehicles assigned so far
    `destination` TEXT NOT NULL,
    `instructions` TEXT,
    `duration_days` INTEGER NOT NULL, -- Number of days the fleet is needed
    `start_date` TEXT NOT NULL, -- When the rental starts
    `expected_return_date` TEXT, -- When the fleet is expected back (calculated)
    `actual_return_date` TEXT, -- When the fleet was actually returned
    `status` TEXT DEFAULT 'Pending', -- Pending, Assigned, In Transit, Completed, Returned
    `order_timestamp` REAL NOT NULL,
    `total_cost` REAL DEFAULT 0.0, -- Total cost of the rental
    FOREIGN KEY(`user_id`) REFERENCES `Users`(`user_id`)
);
""")

# NEW TABLE: FleetOrderAssignments - Track which specific vehicles are assigned
cursor.execute("""
CREATE TABLE IF NOT EXISTS `FleetOrderAssignments` (
    `assignment_id` INTEGER PRIMARY KEY NOT NULL UNIQUE,
    `fleetorder_id` INTEGER NOT NULL,
    `fleet_id` INTEGER NOT NULL,
    `assignment_timestamp` REAL NOT NULL,
    `return_timestamp` REAL, -- When this specific vehicle was returned
    `status` TEXT DEFAULT 'Active', -- Active, Returned
    FOREIGN KEY(`fleetorder_id`) REFERENCES `FleetOrders`(`fleetorder_id`),
    FOREIGN KEY(`fleet_id`) REFERENCES `Fleet`(`fleet_id`)
);
""")

# NEW TABLE: BulkOrders - For bulk product orders with delivery
cursor.execute("""
CREATE TABLE IF NOT EXISTS `BulkOrders` (
    `bulkorder_id` INTEGER PRIMARY KEY NOT NULL UNIQUE,
    `user_id` INTEGER NOT NULL,
    `fleet_id` INTEGER,  -- Optional, assigned later
    `product_category` TEXT NOT NULL, -- What type of product (Fuel, Gas, Oil, etc.)
    `product_type` TEXT NOT NULL, -- Specific product (Unleaded Premium, 6kg Gas Cylinder, etc.)
    `quantity_requested` INTEGER NOT NULL, -- Amount requested (liters, kg, etc.)
    `delivery_address` TEXT NOT NULL, -- Delivery destination
    `total_cost` REAL DEFAULT 0.0, -- Estimated total cost
    `status` TEXT DEFAULT 'Pending', -- Pending, Confirmed, In Transit, Delivered, Cancelled
    `order_timestamp` REAL NOT NULL,
    FOREIGN KEY(`user_id`) REFERENCES `Users`(`user_id`),
    FOREIGN KEY(`fleet_id`) REFERENCES `Fleet`(`fleet_id`)  -- Reference Fleet table
);
""")

# -------------------------------
# ADD NEW COLUMNS FOR PING LOCATION TRACKING
# These ALTER TABLE statements must run AFTER the tables are created
# but BEFORE any data is inserted into them.
# -------------------------------

# Add location tracking columns to Fleet table
cursor.execute("ALTER TABLE Fleet ADD COLUMN last_known_location TEXT DEFAULT NULL;")
cursor.execute("ALTER TABLE Fleet ADD COLUMN last_known_lat REAL DEFAULT NULL;")
cursor.execute("ALTER TABLE Fleet ADD COLUMN last_known_lng REAL DEFAULT NULL;")
cursor.execute("ALTER TABLE Fleet ADD COLUMN last_location_update REAL DEFAULT NULL;")
cursor.execute("ALTER TABLE GasRefillOrders ADD COLUMN fleet_id INTEGER DEFAULT NULL;")

# -------------------------------
# Insert default admin employee
# -------------------------------
cursor.execute("""
INSERT OR IGNORE INTO Employees (
    employee_id, first_name, last_name, phone_number, email, password,
    otp, otp_timestamp, location, role, status, last_login
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    BASE_EMPLOYEE + 1, "Admin", "User", 1234567890, "admin@shopfleet.com",
    hash_password("admin123"),
    "000000", int(time.time()),
    "HQ", "Admin", "Active", int(time.time())
))

# -------------------------------
# Insert extra employees
# -------------------------------
roles = {
    "Driver": 3,
    "ProductManager": 3,
    "Admin": 2,
    "Financer": 3,
    "CustomerService": 3,
    "FleetManager": 2
}
employee_id = BASE_EMPLOYEE + 2
for role, count in roles.items():
    for i in range(1, count + 1):
        cursor.execute("""
        INSERT OR IGNORE INTO Employees (
            employee_id, first_name, last_name, phone_number, email, password,
            otp, otp_timestamp, location, role, status, last_login
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            employee_id,
            role, f"User{i}", 700000000 + employee_id % 1000,
            f"{role.lower()}{i}@shopfleet.com",
            hash_password("password123"),
            "000000", int(time.time()),
            "Nairobi Depot",
            role,
            "Active",
            int(time.time())
        ))
        employee_id += 1

# -------------------------------
# Insert dummy Users
# -------------------------------
for i in range(1, 6):
    cursor.execute("""
    INSERT OR IGNORE INTO Users (
        user_id, first_name, last_name, phone_number, email, password,
        otp, otp_timestamp, location, status, last_login
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        BASE_USER + i, f"User{i}", f"Test{i}", 740000000 + i,
        f"user{i}@mail.com",
        hash_password("pass123"),
        None, None,
        "Nairobi", "Active", int(time.time())
    ))

# -------------------------------
# Insert dummy Products - REDUCED TO 20 PRODUCTS WITH SPECIFIC CATEGORIES
# -------------------------------
product_data = [
    # Lubricants (5 products)
    ("Engine Oil 5L", "Lubricants", "Premium engine oil for all vehicles", "lubricants.jpg", 50, 800, 1200),
    ("Gear Oil 1L", "Lubricants", "High-grade gear oil for transmissions", "lubricants.jpg", 30, 600, 900),
    ("Grease 400g", "Lubricants", "Multi-purpose grease for heavy machinery", "lubricants.jpg", 40, 400, 650),
    ("Hydraulic Oil 5L", "Lubricants", "Hydraulic system oil for industrial use", "lubricants.jpg", 25, 700, 1000),
    ("Brake Fluid", "Lubricants", "DOT 4 brake fluid for safe braking", "lubricants.jpg", 60, 300, 500),
    
    # White Products (5 products)
    ("Unleaded Premium", "White Products", "Premium unleaded petrol for vehicles", "whiteproducts.jpg", 1000, 110, 150),
    ("Low Sulphur Diesel", "White Products", "Clean diesel fuel for vehicles", "whiteproducts.jpg", 1200, 105, 140),
    ("Kerosine", "White Products", "Clean burning kerosine for cooking", "whiteproducts.jpg", 800, 90, 120),
    ("Jet A-1", "White Products", "Aviation fuel for aircraft", "whiteproducts.jpg", 500, 130, 170),
    ("LPG", "White Products", "Liquefied petroleum gas", "whiteproducts.jpg", 200, 120, 160),
    
    # Gas Cylinder (5 products)
    ("6kg Gas Cylinder", "Gas Cylinder", "Standard 6kg gas cylinder", "cylinder.jpg", 150, 1400, 2000),
    ("12kg Gas Cylinder", "Gas Cylinder", "Standard 12kg gas cylinder", "cylinder.jpg", 120, 2700, 3500),
    ("18kg Gas Cylinder", "Gas Cylinder", "Standard 18kg gas cylinder", "cylinder.jpg", 80, 3900, 4800),
    ("24kg Gas Cylinder", "Gas Cylinder", "Standard 24kg gas cylinder", "cylinder.jpg", 60, 4800, 5800),
    ("32kg Gas Cylinder", "Gas Cylinder", "Standard 32kg gas cylinder", "cylinder.jpg", 40, 6000, 7200),
    
    # Engine Oil (5 products)
    ("Synthetic 5W-30", "Engine Oil", "Synthetic engine oil 5W-30", "engineoil.jpg", 70, 1000, 1500),
    ("Mineral 15W-40", "Engine Oil", "Mineral engine oil 15W-40", "engineoil.jpg", 80, 600, 900),
    ("Diesel 10W-30", "Engine Oil", "Diesel engine oil 10W-30", "engineoil.jpg", 65, 800, 1200),
    ("2-Stroke Oil", "Engine Oil", "2-stroke engine oil", "engineoil.jpg", 90, 400, 600),
    ("Compressor Oil", "Engine Oil", "Compressor oil for air compressors", "engineoil.jpg", 50, 700, 1000)
]

product_id = BASE_PRODUCT + 1
for product_name, category, description, image_path, quantity, cost, price in product_data:
    cursor.execute("""
    INSERT OR IGNORE INTO Products (
        product_id, product_name, product_category, product_description,
        product_image, product_quantity, product_cost, retail_price,
        employee_id, product_registration, product_location, location_description, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        product_id,
        product_name,
        category,
        description,
        image_path,  # Changed to reference static/img/ path
        quantity,
        cost,
        price,
        BASE_EMPLOYEE + random.randint(2, 10),  # Changed to employee_id
        f"REG-{product_id:09d}",
        "Nairobi Depot",
        f"{product_name} storage section",
        "Not sold"
    ))
    product_id += 1

# -------------------------------
# Insert dummy Fleet
# -------------------------------
for i in range(1, 6):
    cursor.execute("""
    INSERT OR IGNORE INTO Fleet (
        fleet_id, registration_number, fleet_brand, fleet_model, fleet_category,
        registration_date, employee_id, fleet_mileage, chassis_number,
        cargo_type, max_capacity, status, last_login
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        BASE_FLEET + i, f"KAA-{1000+i}", "Isuzu", f"Model-{i}", "Truck",
        int(time.time()), BASE_EMPLOYEE + random.randint(2, 10),
        random.randint(10000, 200000),
        100000 + i, "Fuel", random.randint(1000, 5000),
        "Active", int(time.time())
    ))

# -------------------------------
# Insert dummy Cart items
# -------------------------------
cart_id = BASE_CART + 1
for user_id in range(1, 6):
    user_cart_items = random.randint(1, 3)  # Reduced to max 3 items per user
    used_products = set()
    for _ in range(user_cart_items):
        product_id = BASE_PRODUCT + random.randint(0, 19)  # Only 20 products now (0-19)
        while product_id in used_products:
            product_id = BASE_PRODUCT + random.randint(0, 19)
        used_products.add(product_id)
        cursor.execute("""
        INSERT OR IGNORE INTO Cart (
            cart_id, product_id, user_id, status
        ) VALUES (?, ?, ?, ?)
        """, (
            cart_id,
            product_id,
            BASE_USER + user_id,
            random.choice(["Wishlist", "In Cart", "Saved for Later"])
        ))
        cart_id += 1

# -------------------------------
# Insert dummy Orders
# -------------------------------
cursor.execute("SELECT cart_id FROM Cart LIMIT 10")
cart_items = cursor.fetchall()
for i, cart_item in enumerate(cart_items):
    cart_id = cart_item[0]
    cursor.execute("SELECT product_id, user_id FROM Cart WHERE cart_id = ?", (cart_id,))
    cart_data = cursor.fetchone()
    if cart_data: # Fixed the typo here
        product_id, user_id = cart_data
        cursor.execute("""
        INSERT OR IGNORE INTO Orders (
            order_id, cart_id, employee_id, fleet_id,
            status, product_destination, product_arrival, otp, otp_timestamp, order_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            BASE_ORDER + i + 1,
            cart_id,
            BASE_EMPLOYEE + random.randint(2, 10),
            BASE_FLEET + random.randint(1, 5),
            random.choice(["Stage 1", "Stage 2", "Completed"]),
            "Customer Location", random.choice([0, 1]),
            str(random.randint(100000, 999999)), int(time.time()), int(time.time())
        ))

# -------------------------------
# 🔥 Insert dummy Gas Refill Orders (for testing)
# -------------------------------
gas_cylinders = [
    ("Standard", "6kg"), ("Standard", "12kg"), ("Standard", "18kg"),
    ("Premium", "6kg"), ("Premium", "12kg")
]
locations = ["Nairobi CBD", "Westlands", "Karen", "Kasarani", "Ruiru"]
for i in range(5):
    user_id = BASE_USER + random.randint(1, 5)
    cylinder_type, size_kg = random.choice(gas_cylinders)
    location = random.choice(locations)
    instructions = f"Gate code: {random.randint(100, 999)}" if random.random() > 0.5 else ""
    cursor.execute("""
    INSERT OR IGNORE INTO GasRefillOrders (
        order_id, user_id, cylinder_type, size_kg, location, instructions,
        status, order_timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        BASE_GAS_REFILL + i,
        user_id,
        cylinder_type,
        size_kg,
        location,
        instructions,
        random.choice(["Pending", "Assigned", "In Transit", "Delivered"]),
        int(time.time()) - random.randint(0, 86400)  # up to 24h ago
    ))

# -------------------------------
# Insert dummy Fleet Orders (for testing) - With duration
# -------------------------------
cargo_types = ["Fuel", "Gas", "Oil", "Chemicals", "General Cargo"]
destinations = ["Nairobi", "Mombasa", "Kisumu", "Eldoret", "Nakuru", "Thika", "Kiambu"]
for i in range(5):
    user_id = BASE_USER + random.randint(1, 5)
    cargo_type = random.choice(cargo_types)
    quantity = random.randint(1, 5)  # Number of vehicles requested
    destination = random.choice(destinations)
    duration_days = random.randint(1, 14)  # 1-14 days
    start_date = time.strftime("%Y-%m-%d", time.localtime(time.time() + random.randint(0, 86400)))  # Today or tomorrow
    expected_return_date = time.strftime("%Y-%m-%d", time.localtime(time.time() + (duration_days * 86400)))
    instructions = f"Delivery instructions: {random.randint(700000000, 799999999)}" if random.random() > 0.5 else ""
    status = random.choice(["Pending", "Assigned", "In Transit", "Completed"])
    
    cursor.execute("""
    INSERT OR IGNORE INTO FleetOrders (
        fleetorder_id, user_id, cargo_type, quantity, assigned_quantity, destination, instructions,
        duration_days, start_date, expected_return_date, status, order_timestamp, total_cost
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        BASE_FLEET_ORDERS + i,
        user_id,
        cargo_type,
        quantity,
        random.randint(0, quantity),  # Some might have partial assignments
        destination,
        instructions,
        duration_days,
        start_date,
        expected_return_date,
        status,
        int(time.time()) - random.randint(0, 86400),  # up to 24h ago
        random.randint(5000, 50000)  # Random cost
    ))

# -------------------------------
# Insert dummy Fleet Order Assignments (for testing)
# -------------------------------
for i in range(8):
    # Get existing fleet orders that have assigned vehicles
    cursor.execute("SELECT fleetorder_id, quantity, assigned_quantity FROM FleetOrders WHERE assigned_quantity > 0 LIMIT 1")
    order_data = cursor.fetchone()
    if order_data:
        fleetorder_id, quantity, assigned_quantity = order_data
        # Create assignments for the assigned vehicles
        for j in range(min(assigned_quantity, 3)):  # Assign up to 3 vehicles per order
            fleet_id = BASE_FLEET + random.randint(1, 5)
            assignment_timestamp = int(time.time()) - random.randint(0, 86400)
            status = random.choice(["Active", "Returned"])
            return_timestamp = assignment_timestamp + (duration_days * 86400) if status == "Returned" else None
            
            cursor.execute("""
            INSERT OR IGNORE INTO FleetOrderAssignments (
                assignment_id, fleetorder_id, fleet_id, assignment_timestamp, return_timestamp, status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                BASE_FLEET_ASSIGNMENTS + i + j,
                fleetorder_id,
                fleet_id,
                assignment_timestamp,
                return_timestamp,
                status
            ))

# -------------------------------
# Insert dummy Bulk Orders (for testing)
# -------------------------------
bulk_categories = ["Fuel", "Gas", "Oil", "Chemicals"]
bulk_products = {
    "Fuel": ["Unleaded Premium", "Low Sulphur Diesel", "Kerosine"],
    "Gas": ["6kg Gas Cylinder", "12kg Gas Cylinder", "18kg Gas Cylinder"],
    "Oil": ["Engine Oil 2kg", "Engine Oil 5kg", "Premium Oil"],
    "Chemicals": ["Industrial Chemicals", "Cleaning Solutions"]
}
delivery_addresses = ["Nairobi CBD", "Westlands", "Karen", "Kasarani", "Ruiru", "Mombasa Town", "Kisumu Center"]

for i in range(5):
    user_id = BASE_USER + random.randint(1, 5)
    category = random.choice(bulk_categories)
    product_type = random.choice(bulk_products[category])
    quantity = random.randint(100, 1000)  # Bulk orders are larger quantities
    delivery_address = random.choice(delivery_addresses)
    total_cost = quantity * random.randint(50, 150)  # Calculate cost based on quantity
    status = random.choice(["Pending", "Confirmed", "In Transit", "Delivered"])
    
    cursor.execute("""
    INSERT OR IGNORE INTO BulkOrders (
        bulkorder_id, user_id, product_category, product_type, 
        quantity_requested, delivery_address, total_cost, status, order_timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        BASE_BULK_ORDERS + i,
        user_id,
        category,
        product_type,
        quantity,
        delivery_address,
        total_cost,
        status,
        int(time.time()) - random.randint(0, 86400 * 7)  # up to 7 days ago
    ))

# -------------------------------
# Insert dummy Reviews
# -------------------------------
for i in range(1, 11):
    cursor.execute("""
    INSERT OR IGNORE INTO Reviews (
        review_id, product_id, text_review, ratings, user_id,
        review_timestamp, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        BASE_REVIEW + i,
        BASE_PRODUCT + random.randint(0, 19),  # Only 20 products
        f"Review {i} for product", random.randint(1, 5),
        BASE_USER + random.randint(1, 5),
        time.strftime("%Y-%m-%d %H:%M:%S"),
        "Not sold"
    ))

# Save and close
conn.commit()
conn.close()

print(f"Database '{db_name}' created successfully with namespaced IDs.")
print(f"✅ Gas Refill Orders table added with sample data (IDs start at {BASE_GAS_REFILL}).")
print(f"✅ Fleet Orders table added with sample data (IDs start at {BASE_FLEET_ORDERS}).")
print(f"✅ Fleet Order Assignments table added with sample data (IDs start at {BASE_FLEET_ASSIGNMENTS}).")
print(f"✅ Bulk Orders table added with sample data (IDs start at {BASE_BULK_ORDERS}).")
print(f"✅ Products table now references employee_id instead of user_id.")
print(f"✅ FleetOrders includes duration tracking and cost calculation.")
print(f"✅ FleetOrderAssignments tracks individual vehicle assignments to orders.")
print(f"✅ BulkOrders tracks large quantity product orders with delivery.")
print(f"✅ Products reduced to 20 items with specific categories and image paths.")