import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_required, current_user
import sqlite3
from user_object import UserObject
from routes import register_blueprints  # ✅ auto-blueprint loader
from functools import wraps
from routes.gasrefill import gasrefill_bp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Add the role_required decorator
def role_required(allowed_roles):
    """
    Decorator to check if the current user has the required role
    allowed_roles: list of allowed roles or a single role string
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            if not hasattr(current_user, 'role'):
                flash('Access denied: Role information not available.', 'danger')
                return redirect(url_for('dashboard'))
            
            user_role = current_user.role
            
            # Convert single role to list for consistent checking
            roles_to_check = allowed_roles if isinstance(allowed_roles, list) else [allowed_roles]
            
            if user_role not in roles_to_check:
                flash(f'Access denied: You need {", ".join(roles_to_check)} role(s) to access this page.', 'danger')
                
                # Redirect based on user's role to avoid infinite loops
                role = user_role.lower()
                if role == "admin":
                    return redirect(url_for("dashboard"))
                elif role in ["FleetManager", "Driver"]:
                    return redirect(url_for("vehiclesmanagefleet"))
                elif role == "Productmanager":
                    return redirect(url_for("manageproduction"))
                elif role == "Customerservice":
                    return redirect(url_for("customersmanage"))
                elif role == "Financer":
                    return redirect(url_for("finances"))
                else:
                    # Default redirect for unknown roles or customer
                    return redirect(url_for("dashboard"))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Initialize app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'petrohub_secret'

# Path to the SQLite database
shopfleetdb = os.path.join(BASE_DIR, 'instance', 'shopfleet.db')

# Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view = "auth.login"  # redirect if not logged in

from datetime import datetime
from flask import Flask # Import Flask if not already imported

# Assuming 'app' is your Flask application instance
@app.template_filter('timestamp_to_datetime')
def timestamp_to_datetime_filter(timestamp):
    """
    Converts a Unix timestamp to a readable datetime string.
    """
    if timestamp:
        try:
            # Convert the timestamp to a datetime object
            dt = datetime.fromtimestamp(timestamp)
            # Format it as a string (you can adjust the format as needed)
            return dt.strftime('%Y-%m-%d %H:%M:%S') # Example format: 2023-10-27 14:30:00
        except (ValueError, TypeError, OSError) as e:
            # Handle potential errors during conversion
            print(f"Error converting timestamp {timestamp}: {e}")
            return "Invalid Timestamp"
    return "Never"


@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(shopfleetdb)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id, first_name, last_name, email, 'customer' as role FROM Users WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    if row:
        conn.close()
        return UserObject(row['user_id'], row['first_name'], row['last_name'], row['email'], row['role'])

    cursor.execute(
        "SELECT employee_id, first_name, last_name, email, role FROM Employees WHERE employee_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return UserObject(row['employee_id'], row['first_name'], row['last_name'], row['email'], row['role'])

    return None


#  Auto-register all Blueprints from routes/
register_blueprints(app)


@app.route("/debug-routes")
def debug_routes():
    try:
        routes = {
            'auth.login': url_for('auth.login'),
            'auth.signup': url_for('auth.signup'),
            'auth.test': url_for('auth.test')
        }
        return f"<pre>{routes}</pre>"
    except Exception as e:
        return f"Error: {str(e)}"
    


@app.template_filter('timestamp_to_datetime')
def timestamp_to_datetime_filter(timestamp):
    """
    Converts a Unix timestamp to a readable datetime string.
    """
    if timestamp:
        try:
            # Convert the timestamp to a datetime object
            dt = datetime.fromtimestamp(timestamp)
            # Format it as a string (you can adjust the format as needed)
            return dt.strftime('%Y-%m-%d %H:%M:%S') # Example format: 2023-10-27 14:30:00
        except (ValueError, TypeError, OSError) as e:
            # Handle potential errors during conversion
            print(f"Error converting timestamp {timestamp}: {e}")
            return "Invalid Timestamp"
    return "Never"


@app.route("/")
def home():
    return render_template("base.html")


@app.route("/debug-all-users")
def debug_all_users():
    conn = sqlite3.connect(shopfleetdb)
    cursor = conn.cursor()

    result = "<h2>Database Users Debug</h2>"

    cursor.execute("SELECT user_id, first_name, last_name, email FROM Users")
    users = cursor.fetchall()
    result += "<h3>Users Table:</h3><ul>"
    for user in users:
        result += f"<li>ID: {user[0]}, Name: {user[1]} {user[2]}, Email: {user[3]}</li>"
    result += "</ul>"

    cursor.execute("SELECT employee_id, first_name, last_name, email, role FROM Employees")
    employees = cursor.fetchall()
    result += "<h3>Employees Table:</h3><ul>"
    for emp in employees:
        result += f"<li>ID: {emp[0]}, Name: {emp[1]} {emp[2]}, Email: {emp[3]}, Role: {emp[4]}</li>"
    result += "</ul>"

    conn.close()
    return result


@app.template_filter('datetime')
def format_datetime(value):
    """Format a timestamp to readable datetime"""
    if value is None:
        return ""
    from datetime import datetime
    return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M')

@app.route("/dashboard")
@role_required(['Driver', 'Admin', 'FleetManager'])
def dashboard():
    conn = sqlite3.connect(shopfleetdb)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get current user (driver) information
    current_user_id = current_user.user_id
    
    # Query 1: Get fleet vehicles assigned to this driver
    cursor.execute("""
        SELECT f.*
        FROM Fleet f 
        WHERE f.employee_id = ?
    """, (current_user_id,))
    assigned_fleets = cursor.fetchall()
    
    # Query 2: Get product delivery orders assigned to this driver's fleet vehicles
    cursor.execute("""
        SELECT o.*, p.product_name, p.product_category, p.retail_price,
               u.first_name as customer_first, u.last_name as customer_last,
               u.location as customer_location,
               c.status as cart_status
        FROM Orders o
        JOIN Fleet f ON o.fleet_id = f.fleet_id  -- Link order to fleet
        JOIN Cart c ON o.cart_id = c.cart_id
        JOIN Products p ON c.product_id = p.product_id
        JOIN Users u ON c.user_id = u.user_id
        WHERE f.employee_id = ? AND o.status != 'Completed'  -- Driver's fleet vehicles
        ORDER BY o.order_timestamp DESC
    """, (current_user_id,))
    product_orders = cursor.fetchall()
    
    # Query 3: Get gas refill orders assigned to this driver's fleet vehicles
    cursor.execute("""
        SELECT g.*, u.first_name as customer_first, u.last_name as customer_last
        FROM GasRefillOrders g
        JOIN Fleet f ON g.fleet_id = f.fleet_id  -- Link gas order to fleet
        JOIN Users u ON g.user_id = u.user_id
        WHERE f.employee_id = ? AND g.status IN ('Assigned', 'In Transit')
        ORDER BY g.order_timestamp DESC
    """, (current_user_id,))
    gas_orders = cursor.fetchall()
    
    # Query 4: Get fleet rental orders with assignments for this driver
    cursor.execute("""
        SELECT fo.*, fa.assignment_id, fa.status as assignment_status,
               f.registration_number, f.fleet_brand, f.fleet_model,
               u.first_name as customer_first, u.last_name as customer_last,
               u.location as customer_location
        FROM FleetOrderAssignments fa
        JOIN FleetOrders fo ON fa.fleetorder_id = fo.fleetorder_id
        JOIN Fleet f ON fa.fleet_id = f.fleet_id
        JOIN Users u ON fo.user_id = u.user_id
        WHERE f.employee_id = ? AND fa.status = 'Active'
        ORDER BY fo.start_date DESC
    """, (current_user_id,))
    fleet_rental_orders = cursor.fetchall()
    
    # Get driver stats - Updated to reflect the correct relationship
    cursor.execute("""
        SELECT COUNT(*) as total_product_orders
        FROM Orders o
        JOIN Fleet f ON o.fleet_id = f.fleet_id
        WHERE f.employee_id = ?
    """, (current_user_id,))
    total_product_orders = cursor.fetchone()['total_product_orders']
    
    cursor.execute("""
        SELECT COUNT(*) as total_fleet_assignments
        FROM FleetOrderAssignments fa
        JOIN Fleet f ON fa.fleet_id = f.fleet_id
        WHERE f.employee_id = ? AND fa.status = 'Active'
    """, (current_user_id,))
    total_fleet_assignments = cursor.fetchone()['total_fleet_assignments']
    
    cursor.execute("""
        SELECT COUNT(*) as completed_orders
        FROM Orders o
        JOIN Fleet f ON o.fleet_id = f.fleet_id
        WHERE f.employee_id = ? AND o.status = 'Completed'
    """, (current_user_id,))
    completed_orders = cursor.fetchone()['completed_orders']
    
    # For gas orders stats - showing only driver's assigned gas orders
    cursor.execute("""
        SELECT COUNT(*) as total_gas_orders
        FROM GasRefillOrders g
        JOIN Fleet f ON g.fleet_id = f.fleet_id
        WHERE f.employee_id = ? AND g.status IN ('Assigned', 'In Transit')
    """, (current_user_id,))
    total_gas_orders = cursor.fetchone()['total_gas_orders']
    
    stats = {
        'total_product_orders': total_product_orders,
        'total_gas_orders': total_gas_orders,
        'total_fleet_assignments': total_fleet_assignments,
        'completed_orders': completed_orders
    }
    
    conn.close()
    
    return render_template("fleet/adminside_fleet/dashboard.html",
                         assigned_fleets=assigned_fleets,
                         product_orders=product_orders,
                         gas_orders=gas_orders,  # Now shows only driver's assigned gas orders
                         fleet_rental_orders=fleet_rental_orders,
                         stats=stats)


@app.route("/vehicles")
@role_required(['FleetManager', 'Admin', 'Driver'])
def vehicles():
    return render_template("fleet/adminside_fleet/vehicles.html")


@app.route("/editfleet/<int:fleet_id>", methods=['GET', 'POST'])
@role_required(['FleetManager', 'Admin', 'Driver'])
def editfleet(fleet_id):
    conn = sqlite3.connect(shopfleetdb)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get the fleet data
    cursor.execute("""
        SELECT f.*, 
               e.first_name as driver_first_name, 
               e.last_name as driver_last_name
        FROM Fleet f
        LEFT JOIN Employees e ON f.employee_id = e.employee_id
        WHERE f.fleet_id = ?
    """, (fleet_id,))
    fleet = cursor.fetchone()
    
    if not fleet:
        flash("Fleet not found!", "error")
        return redirect(url_for('vehiclesmanagefleet'))

    # Check if fleet has a driver assigned
    if fleet['employee_id'] and fleet['employee_id'] != '0':
        flash("Cannot edit a fleet that has a driver assigned!", "error")
        return redirect(url_for('vehiclesmanagefleet'))

    if request.method == 'POST':
        # Get form data
        registration_number = request.form.get('registration_number')
        fleet_brand = request.form.get('fleet_brand')
        fleet_model = request.form.get('fleet_model')
        fleet_category = request.form.get('fleet_category')
        registration_date = request.form.get('registration_date')
        fleet_mileage = request.form.get('fleet_mileage')
        chassis_number = request.form.get('chassis_number')
        cargo_type = request.form.get('cargo_type')
        max_capacity = request.form.get('max_capacity')

        # Validate required fields
        if not all([registration_number, fleet_brand, fleet_model, fleet_category, 
                   registration_date, fleet_mileage, chassis_number, cargo_type, max_capacity]):
            flash("All fields are required!", "error")
        else:
            try:
                # Update the fleet record
                cursor.execute("""
                    UPDATE Fleet 
                    SET registration_number = ?, fleet_brand = ?, fleet_model = ?, 
                        fleet_category = ?, registration_date = ?, fleet_mileage = ?, 
                        chassis_number = ?, cargo_type = ?, max_capacity = ?
                    WHERE fleet_id = ?
                """, (registration_number, fleet_brand, fleet_model, fleet_category, 
                      registration_date, fleet_mileage, chassis_number, cargo_type, 
                      max_capacity, fleet_id))
                
                # For employees, the first parameter in UserObject becomes the user_id attribute
                # In your auth.py: UserObject(employee_data['employee_id'], ...)
                user_id = current_user.user_id  # Use user_id instead of id
                
                # Set the current user as the new driver and set status to 'Assigned'
                cursor.execute("UPDATE Fleet SET employee_id = ?, status = 'Assigned' WHERE fleet_id = ?", 
                              (user_id, fleet_id))
                
                conn.commit()
                flash("Fleet updated successfully and assigned to you!", "success")
                return redirect(url_for('vehiclesmanagefleet'))
            except sqlite3.Error as e:
                flash(f"Database error: {str(e)}", "error")

    conn.close()

    return render_template("fleet/fleet_extend/vehicles/editfleet.html", fleet=fleet)

import time
import requests
from flask import jsonify, flash, redirect, url_for, session # Add session import if using session-based logout
from flask_login import logout_user # Import logout_user from flask_login

import time
import requests
from flask import jsonify, flash, redirect, url_for, session # Add session import if using session-based logout
from flask_login import logout_user # Import logout_user from flask_login

@app.route("/vehiclesmanagefleet", methods=['GET', 'POST'])
@role_required(['FleetManager', 'Admin', 'Driver'])
def vehiclesmanagefleet():
    conn = sqlite3.connect(shopfleetdb)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    filter_status = request.args.get('status')

    if request.method == 'POST':
        fleet_id = request.form.get('fleet_id')
        action = request.form.get('action')  # 'status', 'driver', or 'ping_location'
        
        if action == 'status':
            new_status = request.form.get('status')
            
            if new_status == 'Decommissioned':
                # When setting status to Decommissioned, also remove the driver
                cursor.execute("UPDATE Fleet SET status = ?, employee_id = '0' WHERE fleet_id = ?", (new_status, fleet_id))
                conn.commit()
                flash("Fleet status updated to Decommissioned and driver unassigned!", "success")
            else:
                cursor.execute("UPDATE Fleet SET status = ? WHERE fleet_id = ?", (new_status, fleet_id))
                conn.commit()
                flash("Fleet status updated successfully!", "success")
                
        elif action == 'driver':
            employee_id = request.form.get('employee_id')
            
            # Check if fleet is in a valid status for driver assignment
            cursor.execute("SELECT status FROM Fleet WHERE fleet_id = ?", (fleet_id,))
            fleet_status = cursor.fetchone()['status']
            
            if employee_id == '0':  # No driver selected
                # Remove driver assignment
                cursor.execute("UPDATE Fleet SET employee_id = '0' WHERE fleet_id = ?", (fleet_id,))
                # Set status to 'Unassigned' when removing driver
                cursor.execute("UPDATE Fleet SET status = 'Unassigned' WHERE fleet_id = ?", (fleet_id,))
                conn.commit()
                flash("Driver unassigned successfully and status set to Unassigned!", "success")
            elif fleet_status in ['Decommissioned', 'Active', 'In Service']:
                flash(f"Cannot assign driver to a fleet with status '{fleet_status}'. Fleet must be Idle or Unassigned.", "error")
            else:
                # Check if this driver is already assigned to another fleet
                cursor.execute("SELECT fleet_id FROM Fleet WHERE employee_id = ? AND fleet_id != ?", (employee_id, fleet_id))
                existing_assignment = cursor.fetchone()
                
                if existing_assignment:
                    flash("Driver is already assigned to another fleet. Please unassign first.", "error")
                else:
                    cursor.execute("UPDATE Fleet SET employee_id = ? WHERE fleet_id = ?", (employee_id, fleet_id))
                    # Set status to 'Assigned' when assigning a driver
                    cursor.execute("UPDATE Fleet SET status = 'Assigned' WHERE fleet_id = ?", (fleet_id,))
                    conn.commit()
                    flash("Driver assigned successfully and status set to Assigned!", "success")
        
        elif action == 'ping_location':
            # --- Location Ping Logic with China Restriction ---
            try:
                # Get location from ipinfo.io
                response = requests.get('https://ipinfo.io/json', timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract location information
                    location_str = data.get('loc', 'Unknown')
                    city = data.get('city', 'Unknown')
                    region = data.get('region', 'Unknown')
                    country = data.get('country', 'Unknown')
                    org = data.get('org', 'Unknown')
                    
                    # Check if the country is China
                    if country == 'CN': # 'CN' is the country code for China
                        # Log the user out
                        logout_user() # This logs out the user using Flask-Login
                        # Clear session if also using sessions (optional, Flask-Login usually handles this)
                        # session.clear() 
                        
                        # Return a JSON response indicating logout due to VPN
                        # The frontend JS should handle this specific response
                        return jsonify({'success': False, 'logout': True, 'message': 'Use of VPN detected. You have been logged out.'})

                    # If not China, proceed with updating the database
                    readable_location = f"{city}, {region}, {country}" if city != 'Unknown' else 'Unknown'

                    if location_str != 'Unknown' and ',' in location_str:
                        lat_str, lng_str = location_str.split(',')
                        try:
                            lat = float(lat_str.strip())
                            lng = float(lng_str.strip())
                        except ValueError:
                            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: Invalid coordinate format: {location_str}")
                            return jsonify({'success': False, 'message': 'Invalid location data received'}), 500
                    else:
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: Could not parse coordinates from: {location_str}")
                        return jsonify({'success': False, 'message': 'Could not determine coordinates'}), 500
                    
                    # Update the specific fleet's location in the database
                    cursor.execute("""
                        UPDATE Fleet 
                        SET last_known_location = ?, 
                            last_known_lat = ?, 
                            last_known_lng = ?, 
                            last_location_update = ?
                        WHERE fleet_id = ?
                    """, (readable_location, lat, lng, time.time(), fleet_id))
                    
                    conn.commit()
                    
                    # Optional: Log the update
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Location Update for Fleet {fleet_id}:")
                    print(f"  ISP/Org: {org}")
                    print(f"  Location: {readable_location}")
                    print(f"  Coordinates: {lat}, {lng}")
                    print("-" * 50)
                    
                    return jsonify({'success': True, 'message': 'Location updated successfully', 'lat': lat, 'lng': lng, 'location': readable_location})
                    
                else:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: Could not fetch location")
                    print(f"  Status Code: {response.status_code}")
                    return jsonify({'success': False, 'message': f'Failed to fetch location (Status: {response.status_code})'}), 500
                    
            except requests.exceptions.RequestException as e:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Network Error: {e}")
                return jsonify({'success': False, 'message': f'Network error: {str(e)}'}), 500
            except Exception as e:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}")
                return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500
            # --- End Location Ping Logic with China Restriction ---

        redirect_url = url_for('vehiclesmanagefleet')
        if filter_status:
            redirect_url += f'?status={filter_status}'
        return redirect(redirect_url)

    # Get all employees with role 'Driver'
    cursor.execute("SELECT employee_id, first_name, last_name FROM Employees WHERE role = 'Driver'")
    drivers = cursor.fetchall()

    # Get fleet data with driver names
    if filter_status:
        cursor.execute("""
            SELECT f.*, 
                   e.first_name as driver_first_name, 
                   e.last_name as driver_last_name
            FROM Fleet f
            LEFT JOIN Employees e ON f.employee_id = e.employee_id
            WHERE f.status = ?
            ORDER BY f.fleet_id
        """, (filter_status,))
    else:
        cursor.execute("""
            SELECT f.*, 
                   e.first_name as driver_first_name, 
                   e.last_name as driver_last_name
            FROM Fleet f
            LEFT JOIN Employees e ON f.employee_id = e.employee_id
            ORDER BY f.fleet_id
        """)
    fleets = cursor.fetchall()

    # Get status counts (including the new 'Assigned' status)
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM Fleet 
        GROUP BY status
    """)
    status_counts = cursor.fetchall()

    # Get total fleet count
    cursor.execute("SELECT COUNT(*) as total FROM Fleet")
    total_fleets = cursor.fetchone()['total']

    conn.close()

    return render_template("fleet/fleet_extend/vehicles/managefleet.html",
                           fleets=fleets,
                           drivers=drivers,
                           status_counts=status_counts,
                           current_filter=filter_status,
                           total_fleets=total_fleets)

# Updated route in app.py
@app.route("/vehiclesaddnew", methods=['GET', 'POST'])
@role_required(['FleetManager', 'Admin'])
def vehiclesaddnew():
    if request.method == 'POST':
        # Get form data
        registration_number = request.form.get('registration_number')
        fleet_brand = request.form.get('fleet_brand')
        fleet_model = request.form.get('fleet_model')
        fleet_category = request.form.get('fleet_category')
        registration_date = request.form.get('registration_date')
        fleet_mileage = request.form.get('fleet_mileage')
        chassis_number = request.form.get('chassis_number')
        cargo_type = request.form.get('cargo_type')
        max_capacity = request.form.get('max_capacity')
        
        # Default values as per your requirements
        status = 'Assigned'  # Default status is Assigned
        
        # Get the current logged-in user's ID
        # Based on your load_user function, the ID is stored in user_id for Users 
        # and employee_id for Employees
        employee_id = getattr(current_user, 'id', None) or getattr(current_user, 'user_id', None)
        
        # If we still don't have an employee_id, check if it's an employee
        if not employee_id:
            # Check if the current user has an employee_id attribute (from Employees table)
            employee_id = getattr(current_user, 'employee_id', None)
        
        # If we still can't find it, we might need to handle this case
        if not employee_id:
            flash("Unable to determine employee ID. Please contact administrator.", "danger")
            return redirect(url_for('vehiclesaddnew'))
        
        try:
            conn = sqlite3.connect(shopfleetdb)
            cursor = conn.cursor()
            
            # Check if registration number already exists
            cursor.execute("SELECT registration_number FROM Fleet WHERE registration_number = ?", (registration_number,))
            existing_vehicle = cursor.fetchone()
            
            if existing_vehicle:
                flash(f"Registration number '{registration_number}' already exists. Please use a unique registration number.", "danger")
                conn.close()
                return redirect(url_for('vehiclesaddnew'))
            
            # Insert new vehicle into Fleet table
            cursor.execute("""
                INSERT INTO Fleet (
                    registration_number, fleet_brand, fleet_model, fleet_category,
                    registration_date, employee_id, fleet_mileage, chassis_number,
                    cargo_type, max_capacity, status, last_login
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                registration_number, fleet_brand, fleet_model, fleet_category,
                registration_date, employee_id, fleet_mileage, chassis_number,
                cargo_type, max_capacity, status, 0
            ))
            
            conn.commit()
            conn.close()
            
            flash("Vehicle added successfully!", "success")
            return redirect(url_for('vehiclesmanagefleet'))
            
        except Exception as e:
            flash(f"Error adding vehicle: {str(e)}", "danger")
            print(e)
            return redirect(url_for('vehiclesaddnew'))
    
    # For GET request, no need to fetch employees since it's auto-assigned
    return render_template("fleet/fleet_extend/vehicles/addnew.html")

@app.route("/editproduction/<int:product_id>", methods=['GET', 'POST'])
@role_required(['ProductManager', 'Admin'])
def editproduction(product_id):
    conn = sqlite3.connect(shopfleetdb)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get the product data
    cursor.execute("""
        SELECT p.*, e.first_name, e.last_name 
        FROM Products p 
        LEFT JOIN Employees e ON p.employee_id = e.employee_id
        WHERE p.product_id = ?
    """, (product_id,))
    product = cursor.fetchone()
    
    if not product:
        flash("Product not found!", "error")
        return redirect(url_for('manageproduction'))

    if request.method == 'POST':
        # Get form data
        product_name = request.form.get('product_name')
        product_category = request.form.get('product_category')
        product_description = request.form.get('product_description')
        product_quantity = request.form.get('product_quantity')
        product_cost = request.form.get('product_cost')
        retail_price = request.form.get('retail_price')
        product_location = request.form.get('product_location')
        location_description = request.form.get('location_description')

        # Validate required fields
        if not all([product_name, product_category, product_description, 
                   product_quantity, product_cost, retail_price, product_location]):
            flash("All required fields must be filled!", "error")
        else:
            try:
                # Update the product record
                cursor.execute("""
                    UPDATE Products 
                    SET product_name = ?, product_category = ?, product_description = ?, 
                        product_quantity = ?, product_cost = ?, retail_price = ?, 
                        product_location = ?, location_description = ?
                    WHERE product_id = ?
                """, (product_name, product_category, product_description, 
                      product_quantity, product_cost, retail_price, 
                      product_location, location_description, product_id))
                
                # Set the current user as the editor (using employee_id)
                employee_id = current_user.user_id  # This is actually the employee_id for employees
                cursor.execute("UPDATE Products SET employee_id = ? WHERE product_id = ?", 
                              (employee_id, product_id))
                
                conn.commit()
                flash("Product updated successfully and assigned to you!", "success")
                return redirect(url_for('manageproduction'))
            except sqlite3.Error as e:
                flash(f"Database error: {str(e)}", "error")

    conn.close()

    return render_template("fleet/fleet_extend/production/editproduction.html", product=product)


@app.route("/manageproduction", methods=['GET', 'POST'])
@role_required(['ProductManager', 'Admin'])
def manageproduction():
    conn = sqlite3.connect(shopfleetdb)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    filter_category = request.args.get('category')
    filter_status = request.args.get('status')

    if request.method == 'POST':
        product_id = request.form.get('product_id')
        new_status = request.form.get('status')

        cursor.execute("UPDATE Products SET status = ? WHERE product_id = ?", (new_status, product_id))
        conn.commit()
        flash("Product status updated successfully!", "success")

        redirect_url = url_for('manageproduction')
        if filter_category:
            redirect_url += f'?category={filter_category}'
        elif filter_status:
            redirect_url += f'?status={filter_status}'
        return redirect(redirect_url)

    # Build query based on filters
    query = "SELECT p.*, e.first_name, e.last_name FROM Products p LEFT JOIN Employees e ON p.employee_id = e.employee_id"
    params = []
    
    if filter_category:
        query += " WHERE p.product_category = ?"
        params.append(filter_category)
    elif filter_status:
        query += " WHERE p.status = ?"
        params.append(filter_status)
    
    query += " ORDER BY p.product_registration DESC"
    
    cursor.execute(query, params)
    products = cursor.fetchall()

    # Get category counts
    cursor.execute("""
        SELECT product_category, COUNT(*) as count 
        FROM Products 
        GROUP BY product_category
    """)
    category_counts = cursor.fetchall()
    
    # Get status counts
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM Products 
        GROUP BY status
    """)
    status_counts = cursor.fetchall()

    # Get total product count
    cursor.execute("SELECT COUNT(*) as total FROM Products")
    total_products = cursor.fetchone()['total']

    conn.close()

    return render_template("fleet/fleet_extend/production/manageproduction.html",
                           products=products,
                           category_counts=category_counts,
                           status_counts=status_counts,
                           current_category=filter_category,
                           current_status=filter_status,
                           total_products=total_products)


import os
import datetime
from werkzeug.utils import secure_filename

# Add configuration for file uploads
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB max file size

# Make sure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/addnewproduction", methods=['GET', 'POST'])
@role_required(['ProductManager', 'Admin'])
def addnewproduction():
    if request.method == 'POST':
        # Get form data
        product_name = request.form.get('product_name')
        product_category = request.form.get('product_category')
        product_description = request.form.get('product_description')
        product_quantity = request.form.get('product_quantity')
        product_cost = request.form.get('product_cost')
        retail_price = request.form.get('retail_price')
        product_location = request.form.get('product_location')
        location_description = request.form.get('location_description', '')
        
        # Handle file upload
        product_image_filename = ''
        if 'product_image' in request.files:
            file = request.files['product_image']
            if file and file.filename != '' and allowed_file(file.filename):
                # Generate unique filename
                filename = secure_filename(file.filename)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_")
                unique_filename = timestamp + filename
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                # Store just the filename
                product_image_filename = unique_filename
        
        # Default values
        status = 'In Stock'  # Default status is In Stock
        product_registration = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get the current logged-in user's ID - Use employee_id instead of user_id
        employee_id = getattr(current_user, 'id', None) or getattr(current_user, 'user_id', None)
        
        # If we still don't have an employee_id, check if it's an employee
        if not employee_id:
            # Check if the current user has an employee_id attribute (from Employees table)
            employee_id = getattr(current_user, 'employee_id', None)
        
        # If we still can't find it, we might need to handle this case
        if not employee_id:
            flash("Unable to determine employee ID. Please contact administrator.", "danger")
            return redirect(url_for('addnewproduction'))
        
        try:
            conn = sqlite3.connect(shopfleetdb)
            cursor = conn.cursor()
            
            # Insert new product into Products table - Use employee_id instead of user_id
            cursor.execute("""
                INSERT INTO Products (
                    product_name, product_category, product_description, product_image,
                    product_quantity, product_cost, retail_price, employee_id,
                    product_registration, product_location, location_description, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_name, product_category, product_description, product_image_filename,
                product_quantity, product_cost, retail_price, employee_id,
                product_registration, product_location, location_description, status
            ))
            
            conn.commit()
            conn.close()
            
            flash("Product added successfully!", "success")
            return redirect(url_for('manageproduction'))
            
        except Exception as e:
            flash(f"Error adding product: {str(e)}", "danger")
            print(e)
            return redirect(url_for('addnewproduction'))
    
    # For GET request
    return render_template("fleet/fleet_extend/production/addnewproduction.html")


@app.route("/employees")
@role_required(['Admin'])
def employees():
    return render_template("fleet/adminside_fleet/employees/employees.html")


@app.route("/orders")
@role_required(['CustomerService', 'Admin', 'Financer'])
def orders():
    return render_template("fleet/adminside_fleet/orders.html")


# Add this route to your app.py
@app.route("/customersmanage", methods=['GET', 'POST'])
@role_required(['CustomerService', 'Admin'])
def customersmanage():
    conn = sqlite3.connect(shopfleetdb)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    filter_status = request.args.get('status')

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_status = request.form.get('status')

        cursor.execute("UPDATE Users SET status = ? WHERE user_id = ?", (new_status, user_id))
        conn.commit()
        flash("Customer status updated successfully!", "success")

        redirect_url = url_for('customersmanage')
        if filter_status:
            redirect_url += f'?status={filter_status}'
        return redirect(redirect_url)

    if filter_status:
        cursor.execute("SELECT * FROM Users WHERE status = ?", (filter_status,))
    else:
        cursor.execute("SELECT * FROM Users")
    customers = cursor.fetchall()

    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM Users 
        GROUP BY status
    """)
    status_counts = cursor.fetchall()

    # Get total customer count
    cursor.execute("SELECT COUNT(*) as total FROM Users")
    total_customers = cursor.fetchone()['total']

    conn.close()

    return render_template("fleet/fleet_extend/customers/managecustomers.html",
                           customers=customers,
                           status_counts=status_counts,
                           current_filter=filter_status,
                           total_customers=total_customers)


@app.route("/ordersmanage", methods=['GET', 'POST'])
@role_required(['CustomerService', 'Admin', 'Financer', 'Driver'])
def ordersmanage():
    conn = sqlite3.connect(shopfleetdb)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    filter_status = request.args.get('status')

    if request.method == 'POST':
        order_id = request.form.get('order_id')
        action = request.form.get('action')  # 'status' or 'fleet'
        
        if action == 'status':
            new_status = request.form.get('status')
            cursor.execute("UPDATE Orders SET status = ? WHERE order_id = ?", (new_status, order_id))
            conn.commit()
            flash("Order status updated successfully!", "success")
        elif action == 'fleet':
            fleet_id = request.form.get('fleet_id')
            if fleet_id:
                # Update fleet assignment and set status to 'In Transit'
                cursor.execute("UPDATE Orders SET fleet_id = ?, status = 'In Transit' WHERE order_id = ?", (fleet_id, order_id))
                conn.commit()
                flash("Fleet assigned successfully and status set to In Transit!", "success")
            else:
                flash("Please select a fleet vehicle!", "error")

        redirect_url = url_for('ordersmanage')
        if filter_status:
            redirect_url += f'?status={filter_status}'
        return redirect(redirect_url)

    # Get fleets with assigned drivers (status is 'Assigned')
    cursor.execute("""
        SELECT f.fleet_id, f.registration_number, f.fleet_brand, f.fleet_model, 
               e.first_name, e.last_name
        FROM Fleet f
        LEFT JOIN Employees e ON f.employee_id = e.employee_id
        WHERE f.status = 'Assigned' AND f.employee_id != '0' AND f.employee_id IS NOT NULL
        ORDER BY f.registration_number
    """)
    fleets = cursor.fetchall()

    # Fetch orders with related information
    if filter_status:
        cursor.execute("""
            SELECT o.*, 
                   u.first_name as customer_first_name, 
                   u.last_name as customer_last_name,
                   u.email as customer_email,
                   u.location as customer_location,
                   e.first_name as employee_first_name, 
                   e.last_name as employee_last_name,
                   f.registration_number as fleet_registration,
                   c.status as cart_status
            FROM Orders o
            LEFT JOIN Cart c ON o.cart_id = c.cart_id
            LEFT JOIN Users u ON c.user_id = u.user_id
            LEFT JOIN Employees e ON o.employee_id = e.employee_id
            LEFT JOIN Fleet f ON o.fleet_id = f.fleet_id
            WHERE o.status = ?
            ORDER BY o.order_timestamp DESC
        """, (filter_status,))
    else:
        cursor.execute("""
            SELECT o.*, 
                   u.first_name as customer_first_name, 
                   u.last_name as customer_last_name,
                   u.email as customer_email,
                   u.location as customer_location,
                   e.first_name as employee_first_name, 
                   e.last_name as employee_last_name,
                   f.registration_number as fleet_registration,
                   c.status as cart_status
            FROM Orders o
            LEFT JOIN Cart c ON o.cart_id = c.cart_id
            LEFT JOIN Users u ON c.user_id = u.user_id
            LEFT JOIN Employees e ON o.employee_id = e.employee_id
            LEFT JOIN Fleet f ON o.fleet_id = f.fleet_id
            ORDER BY o.order_timestamp DESC
        """)
    
    orders = cursor.fetchall()

    # Process orders to extract detailed cart information
    processed_orders = []
    for order in orders:
        order_dict = dict(order)
        
        # Parse cart items from cart status (where we stored the detailed info)
        cart_status = order_dict.get('cart_status', '')
        parsed_items = []
        
        # Extract cart items from cart status
        if 'Order_Items:' in cart_status:
            try:
                cart_details_str = cart_status.split('Order_Items:')[1]
                items = cart_details_str.split('; ')
                for item in items:
                    # Parse: "Product Name (ID: 123) x2 - Location: Warehouse A"
                    parsed_item = {
                        'name': 'Unknown',
                        'id': 'Unknown',
                        'quantity': '1',
                        'location': 'Unknown'
                    }
                    
                    try:
                        # Extract name
                        if ' (ID: ' in item:
                            name_part = item.split(' (ID: ')[0]
                            parsed_item['name'] = name_part
                        
                        # Extract ID
                        if ' (ID: ' in item and ') x' in item:
                            id_part = item.split(' (ID: ')[1].split(') x')[0]
                            parsed_item['id'] = id_part
                        
                        # Extract quantity and location
                        if ') x' in item and ' - Location: ' in item:
                            qty_loc_part = item.split(') x')[1]
                            if ' - Location: ' in qty_loc_part:
                                qty_part = qty_loc_part.split(' - Location: ')[0]
                                loc_part = qty_loc_part.split(' - Location: ')[1]
                                parsed_item['quantity'] = qty_part
                                parsed_item['location'] = loc_part
                            else:
                                parsed_item['quantity'] = qty_loc_part
                    except:
                        # If parsing fails, use the raw item
                        parsed_item['name'] = item
                    
                    parsed_items.append(parsed_item)
            except:
                pass
        
        order_dict['parsed_items'] = parsed_items
        processed_orders.append(order_dict)

    # Get status counts
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM Orders 
        GROUP BY status
    """)
    status_counts = cursor.fetchall()

    # Get total orders count
    cursor.execute("SELECT COUNT(*) as total FROM Orders")
    total_orders = cursor.fetchone()['total']

    conn.close()

    return render_template("fleet/fleet_extend/orders/manageorders.html",
                           orders=processed_orders,
                           fleets=fleets,
                           status_counts=status_counts,
                           current_filter=filter_status,
                           total_orders=total_orders)


@app.route("/fleetordersmanage", methods=['GET', 'POST'])
@role_required(['CustomerService', 'Admin', 'Financer', 'FleetManager'])
def fleet_orders_manage():
    conn = sqlite3.connect(shopfleetdb)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    filter_status = request.args.get('status')

    if request.method == 'POST':
        fleetorder_id = request.form.get('fleetorder_id')
        action = request.form.get('action')  # 'status' or 'fleet_assignment'
        
        if action == 'status':
            new_status = request.form.get('status')
            cursor.execute("UPDATE FleetOrders SET status = ? WHERE fleetorder_id = ?", (new_status, fleetorder_id))
            conn.commit()
            flash("Fleet order status updated successfully!", "success")
        elif action == 'fleet_assignment':
            fleet_id = request.form.get('fleet_id')
            if fleet_id:
                # Create assignment in FleetOrderAssignments table
                assignment_timestamp = time.time()
                cursor.execute("""
                    INSERT INTO FleetOrderAssignments (fleetorder_id, fleet_id, assignment_timestamp, status)
                    VALUES (?, ?, ?, 'Active')
                """, (fleetorder_id, fleet_id, assignment_timestamp))
                
                # Update assigned quantity in FleetOrders
                cursor.execute("""
                    UPDATE FleetOrders 
                    SET assigned_quantity = assigned_quantity + 1, 
                        status = CASE 
                            WHEN assigned_quantity + 1 >= quantity THEN 'Assigned'
                            ELSE 'Partially Assigned'
                        END
                    WHERE fleetorder_id = ?
                """, (fleetorder_id,))
                
                conn.commit()
                flash("Fleet vehicle assigned successfully!", "success")
            else:
                flash("Please select a fleet vehicle!", "error")

        redirect_url = url_for('fleet_orders_manage')
        if filter_status:
            redirect_url += f'?status={filter_status}'
        return redirect(redirect_url)

    # Get fleets with assigned drivers (status is 'Assigned')
    cursor.execute("""
        SELECT f.fleet_id, f.registration_number, f.fleet_brand, f.fleet_model, 
               e.first_name, e.last_name
        FROM Fleet f
        LEFT JOIN Employees e ON f.employee_id = e.employee_id
        WHERE f.status = 'Assigned' AND f.employee_id != '0' AND f.employee_id IS NOT NULL
        ORDER BY f.registration_number
    """)
    fleets = cursor.fetchall()

    # Fetch fleet orders with related information
    if filter_status:
        cursor.execute("""
            SELECT fo.*, 
                   u.first_name as customer_first_name, 
                   u.last_name as customer_last_name,
                   u.email as customer_email,
                   u.location as customer_location,
                   u.phone_number as customer_phone,
                   -- Get assignment count
                   (SELECT COUNT(*) FROM FleetOrderAssignments WHERE fleetorder_id = fo.fleetorder_id AND status = 'Active') as active_assignments
            FROM FleetOrders fo
            LEFT JOIN Users u ON fo.user_id = u.user_id
            WHERE fo.status = ?
            ORDER BY fo.order_timestamp DESC
        """, (filter_status,))
    else:
        cursor.execute("""
            SELECT fo.*, 
                   u.first_name as customer_first_name, 
                   u.last_name as customer_last_name,
                   u.email as customer_email,
                   u.location as customer_location,
                   u.phone_number as customer_phone,
                   -- Get assignment count
                   (SELECT COUNT(*) FROM FleetOrderAssignments WHERE fleetorder_id = fo.fleetorder_id AND status = 'Active') as active_assignments
            FROM FleetOrders fo
            LEFT JOIN Users u ON fo.user_id = u.user_id
            ORDER BY fo.order_timestamp DESC
        """)
    
    orders = cursor.fetchall()

    # Get active assignments for each order
    order_assignments = {}
    for order in orders:
        cursor.execute("""
            SELECT foa.*, f.registration_number, f.fleet_brand, f.fleet_model,
                   e.first_name as driver_first, e.last_name as driver_last
            FROM FleetOrderAssignments foa
            JOIN Fleet f ON foa.fleet_id = f.fleet_id
            LEFT JOIN Employees e ON f.employee_id = e.employee_id
            WHERE foa.fleetorder_id = ? AND foa.status = 'Active'
            ORDER BY foa.assignment_timestamp DESC
        """, (order['fleetorder_id'],))
        order_assignments[order['fleetorder_id']] = cursor.fetchall()

    # Get status counts
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM FleetOrders 
        GROUP BY status
    """)
    status_counts = cursor.fetchall()

    # Get total orders count
    cursor.execute("SELECT COUNT(*) as total FROM FleetOrders")
    total_orders = cursor.fetchone()['total']

    conn.close()

    return render_template("fleet/fleet_extend/orders/managefleetorders.html",
                           orders=orders,
                           fleets=fleets,
                           status_counts=status_counts,
                           current_filter=filter_status,
                           total_orders=total_orders,
                           order_assignments=order_assignments)


@app.route("/vieworders")
@login_required
def vieworders():
    # Only allow customers to view their own orders
    # if current_user.role != "customer":
    #     flash("Access denied. Only customers can view their orders.", "danger")
    #     return redirect(url_for('dashboard'))  # or appropriate redirect
    
    conn = sqlite3.connect(shopfleetdb)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get the current user's user_id - use user_id from UserObject
    current_user_id = current_user.user_id

    # Fetch orders for the current user
    cursor.execute("""
        SELECT o.*, 
               u.first_name as customer_first_name, 
               u.last_name as customer_last_name,
               u.email as customer_email,
               u.location as customer_location,
               e.first_name as employee_first_name, 
               e.last_name as employee_last_name,
               f.registration_number as fleet_registration,
               c.status as cart_status
        FROM Orders o
        LEFT JOIN Cart c ON o.cart_id = c.cart_id
        LEFT JOIN Users u ON c.user_id = u.user_id
        LEFT JOIN Employees e ON o.employee_id = e.employee_id
        LEFT JOIN Fleet f ON o.fleet_id = f.fleet_id
        WHERE c.user_id = ?
        ORDER BY o.order_timestamp DESC
    """, (current_user_id,))
    
    orders = cursor.fetchall()

    # Process orders to extract detailed cart information and calculate total
    processed_orders = []
    for order in orders:
        order_dict = dict(order)
        
        # Parse cart items from cart status (where we stored the detailed info)
        cart_status = order_dict.get('cart_status', '')
        parsed_items = []
        
        # Extract cart items from cart status
        if 'Order_Items:' in cart_status:
            try:
                cart_details_str = cart_status.split('Order_Items:')[1]
                items = cart_details_str.split('; ')
                for item in items:
                    # Parse: "Product Name (ID: 123) x2 - Location: Warehouse A"
                    parsed_item = {
                        'name': 'Unknown',
                        'id': 'Unknown',
                        'quantity': '1',
                        'location': 'Unknown'
                    }
                    
                    try:
                        # Extract name
                        if ' (ID: ' in item:
                            name_part = item.split(' (ID: ')[0]
                            parsed_item['name'] = name_part
                        
                        # Extract ID
                        if ' (ID: ' in item and ') x' in item:
                            id_part = item.split(' (ID: ')[1].split(') x')[0]
                            parsed_item['id'] = id_part
                        
                        # Extract quantity and location
                        if ') x' in item and ' - Location: ' in item:
                            qty_loc_part = item.split(') x')[1]
                            if ' - Location: ' in qty_loc_part:
                                qty_part = qty_loc_part.split(' - Location: ')[0]
                                loc_part = qty_loc_part.split(' - Location: ')[1]
                                parsed_item['quantity'] = qty_part
                                parsed_item['location'] = loc_part
                            else:
                                parsed_item['quantity'] = qty_loc_part
                    except:
                        # If parsing fails, use the raw item
                        parsed_item['name'] = item
                    
                    parsed_items.append(parsed_item)
            except:
                pass
        
        # Calculate total amount for this order
        total_amount = 0
        for item in parsed_items:
            if item['id'] != 'Unknown' and str(item['id']).isdigit():
                # Get the product price from the database
                try:
                    cursor.execute("""
                        SELECT retail_price FROM Products 
                        WHERE product_id = ?
                    """, (int(item['id']),))
                    product = cursor.fetchone()
                    if product:
                        retail_price = product['retail_price']
                        quantity = int(item['quantity']) if str(item['quantity']).isdigit() else 1
                        total_amount += retail_price * quantity
                except ValueError:
                    # Skip if there's an issue with parsing
                    continue
        
        order_dict['parsed_items'] = parsed_items
        order_dict['total_amount'] = total_amount
        processed_orders.append(order_dict)

    # Get status counts for current user's orders only
    cursor.execute("""
        SELECT o.status, COUNT(*) as count 
        FROM Orders o
        LEFT JOIN Cart c ON o.cart_id = c.cart_id
        WHERE c.user_id = ?
        GROUP BY o.status
    """, (current_user_id,))
    status_counts = cursor.fetchall()

    # Get total orders count for current user
    cursor.execute("""
        SELECT COUNT(*) as total 
        FROM Orders o
        LEFT JOIN Cart c ON o.cart_id = c.cart_id
        WHERE c.user_id = ?
    """, (current_user_id,))
    total_orders = cursor.fetchone()['total']

    conn.close()

    return render_template("fleet/fleet_extend/customers/vieworders.html",
                           orders=processed_orders,
                           status_counts=status_counts,
                           current_filter=None,  # No filter for user view
                           total_orders=total_orders)


@app.route("/finances")
@role_required(['Financer', 'Admin'])
def finances():
    return render_template("fleet/adminside_fleet/finances.html")


@app.route("/reports")
@role_required(['Admin', 'Financer', 'ProductManager'])
def reports():
    return render_template("fleet/adminside_fleet/reports.html")


@app.route("/bulk", methods=["GET", "POST"])
@login_required
def bulkgoods():
    if request.method == "POST":
        product_category = request.form.get("product_category")
        product_type = request.form.get("product_type")
        quantity_requested = request.form.get("quantity_requested")
        destination_route = request.form.get("destination_route")
        destination_town = request.form.get("destination_town")
        additional_instructions = request.form.get("additional_instructions", "").strip()
    
        # Combine route + town for full delivery address
        delivery_address = f"{destination_route} → {destination_town}"
        if additional_instructions:
            delivery_address += f" | {additional_instructions}"

        
        # Validation
        if not all([product_category, product_type, quantity_requested, delivery_address]):
            flash("Please fill all required fields.", "danger")
            return render_template("shop/bulk.html")
        
        try:
            quantity_requested = int(quantity_requested)
            if quantity_requested <= 0:
                flash("Quantity must be greater than 0.", "danger")
                return render_template("shop/bulk.html")
        except ValueError:
            flash("Quantity must be a valid number.", "danger")
            return render_template("shop/bulk.html")
        
        # Calculate cost (you can adjust the pricing logic)
        base_prices = {
            "Fuel": {"Unleaded Premium": 120, "Low Sulphur Diesel": 110, "Kerosine": 100},
            "Gas": {"6kg Gas Cylinder": 1500, "12kg Gas Cylinder": 2800, "18kg Gas Cylinder": 4000},
            "Oil": {"Engine Oil 2kg": 800, "Engine Oil 5kg": 1800, "Premium Oil": 1200},
            "Chemicals": {"Industrial Chemicals": 200, "Cleaning Solutions": 150}
        }
        
        # Get base price for the product
        base_price = base_prices.get(product_category, {}).get(product_type, 100)
        total_cost = quantity_requested * base_price
        
        try:
            conn = sqlite3.connect(shopfleetdb)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO BulkOrders (
                    user_id, product_category, product_type, 
                    quantity_requested, delivery_address, total_cost, 
                    status, order_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                current_user.user_id,
                product_category,
                product_type,
                quantity_requested,
                delivery_address,
                total_cost,
                'Pending',  # Initial status
                time.time()
            ))
            
            order_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            flash(f"Bulk order submitted successfully! Order ID: #{order_id}", "success")
            return redirect(url_for("bulkgoods"))
            
        except Exception as e:
            flash(f"Error submitting bulk order: {str(e)}", "danger")
            return render_template("shop/bulk.html")
    
    return render_template("shop/bulk.html")


@app.route("/my-bulk-orders")
@login_required
def my_bulk_orders():
    conn = sqlite3.connect(shopfleetdb)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get bulk orders for current user
    cursor.execute("""
        SELECT bo.*, u.first_name, u.last_name
        FROM BulkOrders bo
        JOIN Users u ON bo.user_id = u.user_id
        WHERE bo.user_id = ?
        ORDER BY bo.order_timestamp DESC
    """, (current_user.user_id,))
    
    orders = cursor.fetchall()
    conn.close()
    
    return render_template("shop/my_bulk_orders.html", orders=orders)


@app.route("/bulkordersmanage", methods=['GET', 'POST'])
@role_required(['CustomerService', 'Admin', 'Financer', 'FleetManager'])
def bulk_orders_manage():
    conn = sqlite3.connect(shopfleetdb)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    filter_status = request.args.get('status')

    if request.method == 'POST':
        bulkorder_id = request.form.get('bulkorder_id')
        action = request.form.get('action')  # 'status' or 'fleet'
        
        if action == 'status':
            new_status = request.form.get('status')
            cursor.execute("UPDATE BulkOrders SET status = ? WHERE bulkorder_id = ?", (new_status, bulkorder_id))
            conn.commit()
            flash("Bulk order status updated successfully!", "success")
        elif action == 'fleet':
            fleet_id = request.form.get('fleet_id')
            if fleet_id:
                # Update fleet assignment and set status to 'In Transit'
                cursor.execute("UPDATE BulkOrders SET fleet_id = ?, status = 'In Transit' WHERE bulkorder_id = ?", (fleet_id, bulkorder_id))
                conn.commit()
                flash("Fleet assigned successfully and status set to In Transit!", "success")
            else:
                flash("Please select a fleet vehicle!", "error")

        redirect_url = url_for('bulk_orders_manage')
        if filter_status:
            redirect_url += f'?status={filter_status}'
        return redirect(redirect_url)

    # Get fleets with assigned drivers (status is 'Assigned')
    cursor.execute("""
        SELECT f.fleet_id, f.registration_number, f.fleet_brand, f.fleet_model, 
               e.first_name, e.last_name
        FROM Fleet f
        LEFT JOIN Employees e ON f.employee_id = e.employee_id
        WHERE f.status = 'Assigned' AND f.employee_id != '0' AND f.employee_id IS NOT NULL
        ORDER BY f.registration_number
    """)
    fleets = cursor.fetchall()

    # Fetch bulk orders with related information
    if filter_status:
        cursor.execute("""
            SELECT bo.*, 
                   u.first_name as customer_first_name, 
                   u.last_name as customer_last_name,
                   u.email as customer_email,
                   u.location as customer_location,
                   u.phone_number as customer_phone,
                   f.registration_number as fleet_registration
            FROM BulkOrders bo
            LEFT JOIN Users u ON bo.user_id = u.user_id
            LEFT JOIN Fleet f ON bo.fleet_id = f.fleet_id
            WHERE bo.status = ?
            ORDER BY bo.order_timestamp DESC
        """, (filter_status,))
    else:
        cursor.execute("""
            SELECT bo.*, 
                   u.first_name as customer_first_name, 
                   u.last_name as customer_last_name,
                   u.email as customer_email,
                   u.location as customer_location,
                   u.phone_number as customer_phone,
                   f.registration_number as fleet_registration
            FROM BulkOrders bo
            LEFT JOIN Users u ON bo.user_id = u.user_id
            LEFT JOIN Fleet f ON bo.fleet_id = f.fleet_id
            ORDER BY bo.order_timestamp DESC
        """)
    
    orders = cursor.fetchall()

    # Get status counts
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM BulkOrders 
        GROUP BY status
    """)
    status_counts = cursor.fetchall()

    # Get total orders count
    cursor.execute("SELECT COUNT(*) as total FROM BulkOrders")
    total_orders = cursor.fetchone()['total']

    conn.close()

    return render_template("fleet/fleet_extend/orders/managebulkorders.html",
                           orders=orders,
                           fleets=fleets,
                           status_counts=status_counts,
                           current_filter=filter_status,
                           total_orders=total_orders)



if __name__ == '__main__':
    print("\n Open in browser: http://127.0.0.1:5000\n")
    app.run(debug=True, port=5000, use_reloader=True)
