import os
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
import sqlite3

employees_bp = Blueprint("employees", __name__, template_folder="../fleet_extend/employees")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'shopfleet.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# --- Employee List ---
@employees_bp.route("/employees")
@login_required
def employees_home():
    if current_user.role != "Admin":
        flash("⛔ Access denied. Admins only.", "error")
        return redirect(url_for("dashboard"))

    search = request.args.get("search", "")
    filter_role = request.args.get("filter", "")
    page = int(request.args.get("page", 1))
    per_page = 9
    offset = (page - 1) * per_page

    conn = get_db_connection()

    # Base query - use correct column names with aliases
    query = """
        SELECT employee_id AS id,
               first_name AS fname,
               last_name AS lname,
               phone_number,
               email,
               role,
               status
        FROM Employees
    """
    params = []

    # Build WHERE conditions
    where_clauses = []
    
    # 🔍 Search filter - use correct column names
    if search:
        where_clauses.append("(first_name LIKE ? OR last_name LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    # ✅ Status filters
    valid_status_filters = ["Active", "On-leave", "Off", "Inactive"]
    if filter_role in valid_status_filters:
        where_clauses.append("status = ?")
        params.append(filter_role)
    # ✅ Role filters with mapping
    else:
        # Map UI-friendly names to DB values
        role_map = {
            "Drivers": "Driver",
            "Product Managers": "Product Manager",
            "Admins": "Admin",
            "Financers": "Financer",
            "Customer Service": "Customer Service"
        }

        db_role = role_map.get(filter_role, filter_role)
        if db_role:
            where_clauses.append("role = ?")
            params.append(db_role)

    # Apply WHERE clause
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    # Add pagination
    query += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    # Fetch employees
    employees = conn.execute(query, params).fetchall()

    # Count total employees for pagination
    count_query = "SELECT COUNT(*) FROM Employees"
    count_params = []

    count_where_clauses = []

    if search:
        count_where_clauses.append("(first_name LIKE ? OR last_name LIKE ?)")
        count_params.extend([f"%{search}%", f"%{search}%"])

    if filter_role in valid_status_filters:
        count_where_clauses.append("status = ?")
        count_params.append(filter_role)
    else:
        db_role = role_map.get(filter_role, filter_role)
        if db_role:
            count_where_clauses.append("role = ?")
            count_params.append(db_role)

    if count_where_clauses:
        count_query += " WHERE " + " AND ".join(count_where_clauses)

    total = conn.execute(count_query, count_params).fetchone()[0]
    conn.close()

    total_pages = (total // per_page) + (1 if total % per_page else 0)

    # Pass current_filter to template for active button highlighting
    current_filter = filter_role

    return render_template(
        "fleet/adminside_fleet/employees.html",
        employees=employees,
        search=search,
        current_filter=current_filter,
        filter_role=filter_role,
        page=page,
        total_pages=total_pages
    )

# --- Add Employee ---
@employees_bp.route("/employees/add", methods=["GET", "POST"])
@login_required
def add_employee():
    if current_user.role != "Admin":
        flash("⛔ Access denied. Admins only.", "error")
        return redirect(url_for("employees.employees_home"))

    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        role = request.form["role"]
        email = request.form["email"]
        phone_number = request.form.get("phone_number", "")
        location = request.form.get("location", "")  # Get location from form
        password = request.form["password"]  # Get password from form
        generate_otp = request.form.get("generate_otp")  # Check if OTP should be generated

        # Hash the password
        import bcrypt
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        
        # Generate OTP if requested
        import random
        import time
        otp = str(random.randint(100000, 999999)) if generate_otp else "000000"
        otp_timestamp = time.time() if generate_otp else 0.0

        conn = get_db_connection()
        try:
            # Insert with all required fields including password, location, otp, etc.
            conn.execute(
                """INSERT INTO Employees (
                    first_name, last_name, role, email, phone_number, password, 
                    otp, otp_timestamp, location, status, last_login
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    first_name, last_name, role, email, phone_number, 
                    hashed_password, otp, otp_timestamp, location, 
                    "Active", time.time()  # status and last_login
                )
            )
            conn.commit()
            flash("✅ Employee added successfully!", "success")
            return redirect(url_for("employees.employees_home"))
        except sqlite3.IntegrityError as e:
            if "email" in str(e):
                flash("❌ Email already exists. Please use a unique email.", "error")
            else:
                flash(f"❌ Error adding employee: {str(e)}", "error")
            print(e)
        except Exception as e:
            flash(f"❌ Error adding employee: {str(e)}", "error")
            print(e)
        finally:
            conn.close()

    return render_template("fleet_extend/employees/add.html")


# --- Edit Employee ---
@employees_bp.route("/employees/edit/<int:emp_id>", methods=["GET", "POST"])
@login_required
def edit_employee(emp_id):
    if current_user.role != "Admin":
        flash("⛔ Access denied. Admins only.", "error")
        return redirect(url_for("employees.employees_home"))

    conn = get_db_connection()
    emp = conn.execute(
        "SELECT * FROM Employees WHERE employee_id = ?", 
        (emp_id,)
    ).fetchone()

    if not emp:
        flash("⚠️ Employee not found.", "error")
        conn.close()
        return redirect(url_for("employees.employees_home"))

    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        role = request.form["role"]
        email = request.form["email"]
        phone_number = request.form.get("phone_number", emp["phone_number"])

        try:
            conn.execute(
                "UPDATE Employees SET first_name=?, last_name=?, role=?, email=?, phone_number=? WHERE employee_id=?",
                (first_name, last_name, role, email, phone_number, emp_id)
            )
            conn.commit()
            flash("✅ Employee updated successfully!", "success")
            conn.close()
            return redirect(url_for("employees.employees_home"))
        except sqlite3.IntegrityError:
            flash("⚠️ Email already exists.", "error")
        # Don't close yet if error; stay on form

    conn.close()
    return render_template("fleet_extend/employees/edit.html", emp=emp)


# --- Delete Employee ---
@employees_bp.route("/employees/delete/<int:emp_id>", methods=["POST"])
@login_required
def delete_employee(emp_id):
    if current_user.role != "Admin":
        flash("⛔ Access denied. Admins only.", "error")
        return redirect(url_for("employees.employees_home"))

    conn = get_db_connection()
    result = conn.execute(
        "DELETE FROM Employees WHERE employee_id=?", 
        (emp_id,)
    ).rowcount
    conn.commit()
    conn.close()

    if result:
        flash("🗑️ Employee deleted successfully!", "success")
    else:
        flash("⚠️ Employee not found.", "error")
    return redirect(url_for("employees.employees_home"))