# routes/gasrefill.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import sqlite3
from datetime import datetime

# ✅ Only import what you use — no unused imports
gasrefill_bp = Blueprint("gasrefill", __name__, template_folder="../templates/gasrefill")

# ✅ Use your existing DB path
DB_PATH = '../greenwells-operations/greenwells_operations/instance/shopfleet.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- Customer Gas Refill Form ---
@gasrefill_bp.route("/gasrefill", methods=["GET", "POST"])
@login_required
def gas_refill_form():
    if current_user.role != "customer":
        flash("Only customers can request gas refills.", "warning")
        return redirect(url_for("shop.shop_home"))

    # Mock cylinder options (you can later pull from Products table)
    cylinders = [
        {"type": "Standard", "sizes": ["6kg", "12kg", "18kg", "24kg", "32kg"]},
        {"type": "Premium", "sizes": ["6kg", "12kg", "18kg"]}
    ]
    locations = ["Nairobi CBD", "Westlands", "Karen", "Kasarani", "Ruiru", "Thika"]

    if request.method == "POST":
        cylinder_type = request.form.get("cylinder_type")
        size = request.form.get("size")
        location = request.form.get("location")
        instructions = request.form.get("instructions", "").strip()

        if not all([cylinder_type, size, location]):
            flash("Please fill all required fields.", "danger")
            return render_template("gasrefill/customer_request.html", cylinders=cylinders, locations=locations)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            user_id = getattr(current_user, 'user_id', getattr(current_user, 'id', None))
            cursor.execute("""
                INSERT INTO GasRefillOrders (
                    user_id, cylinder_type, size_kg, location, instructions,
                    status, order_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                cylinder_type,
                size,
                location,
                instructions,
                "Pending",
                datetime.now().timestamp()
            ))
            order_id = cursor.lastrowid
            conn.commit()
            conn.close()
            flash("✅ Your gas refill request has been submitted!", "success")
            return redirect(url_for("gasrefill.order_tracking", order_id=order_id))
        except Exception as e:
            flash(f"Error submitting request: {str(e)}", "danger")
            return render_template("gasrefill/customer_request.html", cylinders=cylinders, locations=locations)

    return render_template("gasrefill/customer_request.html", cylinders=cylinders, locations=locations)

# --- Admin Dashboard ---
@gasrefill_bp.route("/gasrefill/admin", methods=["GET", "POST"])
@login_required
def admin_gas_refill_dashboard():
    allowed_roles = ["Admin", "CustomerService", "Financer"]
    if current_user.role not in allowed_roles:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    filter_status = request.args.get('status')

    if request.method == "POST":
        order_id = request.form.get("order_id")
        action = request.form.get("action")  # 'status' or 'fleet'
        
        if action == 'status':
            new_status = request.form.get("status")
            cursor.execute("UPDATE GasRefillOrders SET status = ? WHERE order_id = ?", (new_status, order_id))
            conn.commit()
            flash("✅ Order status updated!", "success")
        elif action == 'fleet':
            fleet_id = request.form.get('fleet_id')
            if fleet_id:
                # Update fleet assignment and set status to 'Assigned' or 'In Transit'
                cursor.execute("UPDATE GasRefillOrders SET fleet_id = ?, status = 'Assigned' WHERE order_id = ?", (fleet_id, order_id))
                conn.commit()
                flash("Fleet assigned successfully and status set to Assigned!", "success")
            else:
                flash("Please select a fleet vehicle!", "error")

        redirect_url = url_for('gasrefill.admin_gas_refill_dashboard')
        if filter_status:
            redirect_url += f'?status={filter_status}'
        return redirect(redirect_url)

    # Get fleets with assigned drivers (for potential fleet assignment - similar to orders page)
    cursor.execute("""
        SELECT f.fleet_id, f.registration_number, f.fleet_brand, f.fleet_model, 
               e.first_name, e.last_name
        FROM Fleet f
        LEFT JOIN Employees e ON f.employee_id = e.employee_id
        WHERE f.status = 'Assigned' AND f.employee_id != '0' AND f.employee_id IS NOT NULL
        ORDER BY f.registration_number
    """)
    fleets = cursor.fetchall()

    # Fetch gas orders with related user information
    if filter_status:
        cursor.execute("""
            SELECT g.*, 
                   u.first_name as first_name, 
                   u.last_name as last_name,
                   u.email as email,
                   u.phone_number as phone_number,
                   u.location as location,
                   f.registration_number as fleet_registration
            FROM GasRefillOrders g
            LEFT JOIN Users u ON g.user_id = u.user_id
            LEFT JOIN Fleet f ON g.fleet_id = f.fleet_id
            WHERE g.status = ?
            ORDER BY g.order_timestamp DESC
        """, (filter_status,))
    else:
        cursor.execute("""
            SELECT g.*, 
                   u.first_name as first_name, 
                   u.last_name as last_name,
                   u.email as email,
                   u.phone_number as phone_number,
                   u.location as location,
                   f.registration_number as fleet_registration
            FROM GasRefillOrders g
            LEFT JOIN Users u ON g.user_id = u.user_id
            LEFT JOIN Fleet f ON g.fleet_id = f.fleet_id
            ORDER BY g.order_timestamp DESC
        """)
    
    orders = cursor.fetchall()

    # Get status counts
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM GasRefillOrders 
        GROUP BY status
    """)
    status_counts = cursor.fetchall()

    # Get total orders count
    cursor.execute("SELECT COUNT(*) as total FROM GasRefillOrders")
    total_orders = cursor.fetchone()['total']

    conn.close()

    return render_template("gasrefill/admin_dashboard.html",
                           orders=orders,
                           fleets=fleets,
                           status_counts=status_counts,
                           current_filter=filter_status,
                           total_orders=total_orders)

# --- Order Tracking ---
@gasrefill_bp.route("/gasrefill/tracking/<int:order_id>")
@login_required
def order_tracking(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT g.*, u.first_name, u.last_name 
        FROM GasRefillOrders g
        JOIN Users u ON g.user_id = u.user_id
        WHERE g.order_id = ?
    """, (order_id,))
    order = cursor.fetchone()
    conn.close()

    if not order or (order['user_id'] != getattr(current_user, 'user_id', None)):
        flash("Order not found or access denied.", "danger")
        return redirect(url_for("gasrefill.gas_refill_form"))

    status_steps = {
        "Pending": 0,
        "Assigned": 1,
        "In Transit": 2,
        "Delivered": 3
    }
    current_step = status_steps.get(order['status'], 0)
    steps = [
        {"label": "Request Received", "active": current_step >= 0},
        {"label": "Assigned to Driver", "active": current_step >= 1},
        {"label": "On the Way", "active": current_step >= 2},
        {"label": "Delivered", "active": current_step >= 3}
    ]

    return render_template("gasrefill/order_tracking.html", order=order, steps=steps)