from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
import sqlite3
from datetime import datetime, timedelta

fleet_bp = Blueprint("fleet", __name__, template_folder="../templates/fleet")

# Database path
DB_PATH = '../greenwells-operations/greenwells_operations/instance/shopfleet.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@fleet_bp.route("/fleetordering", methods=["GET", "POST"])
@login_required
def fleet_home():
    # If user is CUSTOMER → show fleet request form
    if request.method == "POST":
        vehicle_type = request.form.get("vehicle_type")
        quantity = request.form.get("quantity")
        # --- NEW FIELDS ---
        destination_route = request.form.get("destination_route")
        destination_town = request.form.get("destination_town")
        additional_instructions = request.form.get("additional_instructions", "").strip()
        # ------------------

        # --- VALIDATION ---
        if not all([vehicle_type, quantity, destination_route, destination_town]):
            flash("Please fill all required fields.", "danger")
            return render_template("fleet/customer_request.html")
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                flash("Quantity must be greater than 0.", "danger")
                return render_template("fleet/customer_request.html")
        except ValueError:
            flash("Quantity must be a valid number.", "danger")
            return render_template("fleet/customer_request.html")
        # ------------------

        # --- COMBINE NEW FIELDS INTO DESTINATION/INSTRUCTIONS ---
        # Option 1: Combine route and town into 'destination', add instructions separately
        destination = f"{destination_route} → {destination_town}"
        instructions = additional_instructions if additional_instructions else destination # Use combined route/town as fallback
        # Option 2: Combine everything into 'instructions' and use route/town for 'destination'
        # destination = f"{destination_route} → {destination_town}"
        # instructions_parts = [destination]
        # if additional_instructions:
        #     instructions_parts.append(additional_instructions)
        # instructions = " | ".join(instructions_parts)
        # We'll use Option 1 for clarity in the DB.
        # ------------------

        # Auto-fill fields
        duration_days = 10  # Fixed duration
        start_date = datetime.now().strftime('%Y-%m-%d')  # Today's date
        expected_return_date = (datetime.now() + timedelta(days=duration_days)).strftime('%Y-%m-%d')
        order_timestamp = datetime.now().timestamp()
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO FleetOrders (
                    user_id, cargo_type, quantity, assigned_quantity, destination,
                    instructions, duration_days, start_date, expected_return_date,
                    actual_return_date, status, order_timestamp, total_cost
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                current_user.user_id,  # Use user_id from your UserObject
                vehicle_type,  # Using vehicle_type as cargo_type for now
                quantity,
                0,  # assigned_quantity starts at 0
                destination, # Use the combined route/town
                instructions, # Use the instructions field
                duration_days,
                start_date,
                expected_return_date,
                None,  # actual_return_date not set yet
                'Pending',  # Initial status
                order_timestamp,
                0.0  # total_cost starts at 0
            ))
            
            order_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            flash("Your fleet request has been submitted successfully!", "success")
            return redirect(url_for("fleet.fleet_home"))
            
        except Exception as e:
            flash(f"Error submitting request: {str(e)}", "danger")
            return render_template("fleet/customer_request.html")
    
    return render_template("fleet/customer_request.html")

# Additional route for viewing fleet order details (if needed)
@fleet_bp.route("/fleetorders")
@login_required
def fleet_orders():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    
    # Check if user is admin or fleet manager - if so, they can see all orders
    # Otherwise, only show their own orders
    if current_user.role in ['Admin', 'FleetManager']:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fo.*, u.first_name, u.last_name, u.email, u.phone_number
            FROM FleetOrders fo
            JOIN Users u ON fo.user_id = u.user_id
            ORDER BY fo.order_timestamp DESC
        """)
        orders = cursor.fetchall()
    else:
        # Regular customers and other roles can only see their own orders
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fo.*, u.first_name, u.last_name, u.email, u.phone_number
            FROM FleetOrders fo
            JOIN Users u ON fo.user_id = u.user_id
            WHERE fo.user_id = ?
            ORDER BY fo.order_timestamp DESC
        """, (current_user.user_id,))
        orders = cursor.fetchall()
    
    conn.close()
    return render_template("fleet/orders_list.html", orders=orders)