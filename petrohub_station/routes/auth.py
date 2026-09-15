# routes/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
import sqlite3
import bcrypt
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import time
import base64

# Define the database path
#shopfleetdb = '../greenwells-operations/greenwells_operations/instance/shopfleet.db'
shopfleetdb = '../../greenwells_operations/instance/shopfleet.db'

# ✅ Define the blueprint here (no circular import)
auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")

print("Auth blueprint registered")  # Debug line

# Email configuration (update with your email settings)
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',  # Change to your SMTP server
    'smtp_port': 587,
    'email': 'qazgmr4rls@gmail.com',  # Your email
    'password': 'pbtf yndj pxvi wgva'   # Your app password
}

# Allowed email domains
ALLOWED_EMAIL_DOMAINS = [
    'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'live.com',
    'aol.com', 'icloud.com', 'mail.com', 'protonmail.com', 'zoho.com',
    'company.com', 'business.com', 'organization.com', 'enterprise.com',
    'corporate.com', 'firm.com', 'institution.com', 'agency.com',
    'gmail.co.ke', 'yahoo.co.ke', 'outlook.co.ke', 'hotmail.co.ke',  # Kenya specific
    'yahoo.com.ng', 'gmail.com.ng', 'outlook.com.ng',  # Nigeria specific
    'yahoo.com.gh', 'gmail.com.gh', 'outlook.com.gh',  # Ghana specific
    'yahoo.com.za', 'gmail.com.za', 'outlook.com.za'   # South Africa specific
]

def encrypt_otp(otp):
    """Encrypt OTP using bcrypt for storage"""
    if not otp:
        return None
    return bcrypt.hashpw(otp.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_encrypted_otp(plain_otp, encrypted_otp):
    """Verify plain OTP against encrypted OTP"""
    if not plain_otp or not encrypted_otp:
        return False
    return bcrypt.checkpw(plain_otp.encode('utf-8'), encrypted_otp.encode('utf-8'))

def generate_otp():
    """Generate 6-digit OTP"""
    # return str(random.randint(100000, 999999))
    return "123456"  # Temporary fixed OTP for testing

def send_otp_email(email, otp, name):
    """Send OTP via email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['email']
        msg['To'] = email
        msg['Subject'] = 'PetroHub - OTP Verification'

        body = f"""
        Hello {name},
        
        Your OTP code for login is: {otp}
        
        This code will expire in 90 seconds.
        
        If you didn't request this code, please ignore this email.
        
        Best regards,
        PetroHub Team
        """

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        email = "test mail"
        otp = "123456"
        name = "Test User"
        print(f"Temporary OTP for {email}: {otp} {name}")  # Debug line
        return False

def store_otp_in_database(employee_id, otp):
    """Store encrypted OTP and timestamp in database for employee"""
    conn = sqlite3.connect(shopfleetdb)
    cursor = conn.cursor()
    
    # Encrypt the OTP before storing
    encrypted_otp = encrypt_otp(otp) if otp else None
    timestamp = time.time() if otp else None
    
    cursor.execute("""
        UPDATE Employees 
        SET otp = ?, otp_timestamp = ? 
        WHERE employee_id = ?
    """, (encrypted_otp, timestamp, employee_id))
    
    conn.commit()
    conn.close()

def is_otp_valid(employee_id, entered_otp):
    """Check if OTP is valid and not expired for employee"""
    conn = sqlite3.connect(shopfleetdb)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT otp, otp_timestamp 
        FROM Employees 
        WHERE employee_id = ?
    """, (employee_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return False
    
    stored_otp, otp_timestamp = result
    
    if not stored_otp or not otp_timestamp:
        return False
    
    # Verify the OTP using bcrypt
    if not verify_encrypted_otp(entered_otp, stored_otp):
        return False
    
    current_time = time.time()
    
    # 90 seconds expiration
    if current_time - otp_timestamp > 90:
        # Clear expired OTP
        clear_otp(employee_id)
        return False
    
    return True

def clear_otp(employee_id):
    """Clear OTP from database"""
    conn = sqlite3.connect(shopfleetdb)
    cursor = conn.cursor()
    
    # Use empty string instead of NULL to avoid NOT NULL constraint
    cursor.execute("""
        UPDATE Employees 
        SET otp = '', otp_timestamp = 0 
        WHERE employee_id = ?
    """, (employee_id,))
    
    conn.commit()
    conn.close()

def get_pending_employee(employee_id):
    """Get employee data for pending login"""
    conn = sqlite3.connect(shopfleetdb)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT employee_id, first_name, last_name, email, role  
        FROM Employees 
        WHERE employee_id = ?
    """, (employee_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'employee_id': result[0],
            'first_name': result[1],
            'last_name': result[2],
            'email': result[3],
            'role': result[4]
        }
    return None

def is_valid_email_domain(email):
    """Check if email domain is in allowed list"""
    try:
        domain = email.split('@')[1].lower()
        return domain in ALLOWED_EMAIL_DOMAINS
    except:
        return False

def get_allowed_domains_string():
    """Get a formatted string of allowed domains for display"""
    # Group by category for better display
    general_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'live.com', 'aol.com', 'icloud.com', 'mail.com', 'protonmail.com', 'zoho.com']
    official_domains = ['company.com', 'business.com', 'organization.com', 'enterprise.com', 'corporate.com', 'firm.com', 'institution.com', 'agency.com']
    regional_domains = [d for d in ALLOWED_EMAIL_DOMAINS if d not in general_domains and d not in official_domains]
    
    allowed_domains_text = "General: " + ", ".join(general_domains) + " | "
    allowed_domains_text += "Official: " + ", ".join(official_domains)
    
    if regional_domains:
        allowed_domains_text += " | Regional: " + ", ".join(regional_domains)
    
    return allowed_domains_text

# --- Signup ---
@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    print("Signup route accessed")  # Debug line
    from forms import SignupForm
    form = SignupForm()
    if form.validate_on_submit():
        conn = sqlite3.connect(shopfleetdb)
        cursor = conn.cursor()

        email = form.email.data.lower().strip()

        # Check if email domain is allowed
        if not is_valid_email_domain(email):
            allowed_domains = get_allowed_domains_string()
            flash(f"Email domain not allowed. Please use one of these domains: {allowed_domains}", "danger")
            conn.close()
            return render_template("auth/signup.html", form=form)

        # Check if the email already exists
        cursor.execute("SELECT email FROM Users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            flash("Email already registered. Please log in.", "warning")
            return redirect(url_for("auth.login"))

        fname = form.fname.data.strip()
        lname = form.lname.data.strip()
        phone = form.phone.data.strip()
        password = form.password.data.strip()

        # Hash password before saving
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        cursor.execute("""
            INSERT INTO Users (first_name, last_name, phone_number, email, password, location, status, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fname,
            lname,
            phone,
            email,
            hashed_password,
            "Unknown",
            "Active",
            0
        ))

        conn.commit()
        conn.close()

        flash("Account created! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/signup.html", form=form)

# --- Login ---
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    from forms import LoginForm
    form = LoginForm()
    if form.validate_on_submit():
        conn = sqlite3.connect(shopfleetdb)
        cursor = conn.cursor()

        email = form.email.data.lower().strip()
        password = form.password.data
        
        print(f"Attempting login for email: {email}")  # Debug line

        # Check Employees first (admins should be here)
        cursor.execute("SELECT employee_id, password, role, email, first_name, last_name FROM Employees WHERE email = ?", (email,))
        employee = cursor.fetchone()
        
        print(f"Employee result: {employee}")  # Debug line

        if employee:
            employee_id, stored_password, role, emp_email, first_name, last_name,  = employee
            print(f"Found employee: {first_name} {last_name}, role: {role}")  # Debug line
            if bcrypt.checkpw(password.encode("utf-8"), stored_password.encode("utf-8")):
                # Generate and send OTP
                otp = generate_otp()
                print(f"Generated OTP: {otp}")  # Debug line
                
                # Store encrypted OTP in database
                store_otp_in_database(employee_id, otp)
                
                # Send OTP in background thread
                def send_email():
                    send_otp_email(emp_email, otp, f"{first_name} {last_name}")
                
                email_thread = threading.Thread(target=send_email)
                email_thread.start()
                
                conn.close()
                
                # Store employee_id in session for OTP verification
                session['pending_employee_id'] = employee_id
                
                flash(f"OTP sent to your email. Please check your inbox.", "info")
                return redirect(url_for("auth.verify_otp"))
            else:
                flash("Invalid email or password.", "danger")
                conn.close()
                return render_template("auth/login.html", form=form)

        # If not employee, check Users table
        cursor.execute("SELECT user_id, password, first_name, last_name, email FROM Users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        print(f"User result: {user}")  # Debug line

        if user:
            user_id, stored_password, first_name, last_name, user_email = user
            print(f"Found user: {first_name} {last_name}")  # Debug line
            if bcrypt.checkpw(password.encode("utf-8"), stored_password.encode("utf-8")):
                from user_object import UserObject
                user_obj = UserObject(user_id, first_name, last_name, user_email, "customer")
                login_user(user_obj)
                flash("Logged in successfully!", "success")
                return redirect(url_for("shop.shop_home"))
            else:
                flash("Invalid email or password.", "danger")
        else:
            flash("Email does not exist.", "danger")

    return render_template("auth/login.html", form=form)

# --- OTP Verification ---
@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if 'pending_employee_id' not in session:
        flash("No pending login. Please login first.", "warning")
        return redirect(url_for("auth.login"))
    
    employee_id = session['pending_employee_id']
    
    # Get employee data
    employee_data = get_pending_employee(employee_id)
    if not employee_data:
        flash("Invalid session. Please login again.", "danger")
        session.pop('pending_employee_id', None)
        return redirect(url_for("auth.login"))
    
    if request.method == "POST":
        entered_otp = request.form.get("otp")
        
        if is_otp_valid(employee_id, entered_otp):
            # OTP is correct, login the user
            from user_object import UserObject
            user = UserObject(
                employee_data['employee_id'],
                employee_data['first_name'],
                employee_data['last_name'],
                employee_data['email'],
                employee_data['role']
            )
            login_user(user)
            
            # Clear OTP from database
            clear_otp(employee_id)
            
            # Clear session
            session.pop('pending_employee_id', None)
            
            flash(f"Logged in successfully as {employee_data['role']}!", "success")
            
            # Role-based redirect with better user experience
            role = employee_data['role'].lower()
            if role == "admin":
                return redirect(url_for("dashboard"))
            elif role in ["fleetmanager", "driver"]:
                return redirect(url_for("vehicles"))
            elif role == "productmanager":
                return redirect(url_for("manageproduction"))
            elif role == "customerservice":
                return redirect(url_for("customersmanage"))
            elif role == "financer":
                return redirect(url_for("finances"))
            else:
                # Default redirect for unknown roles
                return redirect(url_for("dashboard"))
        else:
            flash("Invalid or expired OTP. Please try again.", "danger")
    
    # Check if there's a pending OTP (GET request)
    conn = sqlite3.connect(shopfleetdb)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT otp_timestamp 
        FROM Employees 
        WHERE employee_id = ?
    """, (employee_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        otp_timestamp = result[0]
        current_time = time.time()
        if current_time - otp_timestamp > 90:
            # OTP expired
            clear_otp(employee_id)
            session.pop('pending_employee_id', None)
            flash("OTP has expired. Please login again.", "danger")
            return redirect(url_for("auth.login"))
    elif not result or not result[0]:
        # No OTP found
        session.pop('pending_employee_id', None)
        flash("No pending OTP. Please login again.", "danger")
        return redirect(url_for("auth.login"))
    
    return render_template("auth/otp_verify.html")

# --- Resend OTP ---
@auth_bp.route("/resend-otp")
def resend_otp():
    if 'pending_employee_id' not in session:
        flash("No pending login. Please login first.", "warning")
        return redirect(url_for("auth.login"))
    
    employee_id = session['pending_employee_id']
    
    # Get employee data
    employee_data = get_pending_employee(employee_id)
    if not employee_data:
        flash("Invalid session. Please login again.", "danger")
        session.pop('pending_employee_id', None)
        return redirect(url_for("auth.login"))
    
    # Check if there's an existing OTP and if it's still valid
    conn = sqlite3.connect(shopfleetdb)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT otp_timestamp 
        FROM Employees 
        WHERE employee_id = ?
    """, (employee_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        otp_timestamp = result[0]
        current_time = time.time()
        if current_time - otp_timestamp <= 90:
            flash("OTP is still valid. Please check your email.", "info")
            return redirect(url_for("auth.verify_otp"))
    
    # Generate new OTP
    otp = generate_otp()
    
    # Store encrypted OTP in database
    store_otp_in_database(employee_id, otp)
    
    # Send OTP in background thread
    def send_email():
        send_otp_email(employee_data['email'], otp, f"{employee_data['first_name']} {employee_data['last_name']}")
    
    email_thread = threading.Thread(target=send_email)
    email_thread.start()
    
    flash("New OTP sent to your email.", "info")
    return redirect(url_for("auth.verify_otp"))

# --- Logout ---
@auth_bp.route("/logout")
@login_required
def logout():
    # Clear any pending OTP if exists
    if 'pending_employee_id' in session:
        clear_otp(session['pending_employee_id'])
        session.pop('pending_employee_id', None)
    
    logout_user()
    flash("You have been logged out.", "info")
    return redirect("/")

# --- Test route (debugging) ---
@auth_bp.route("/test")
def test():
    return "Auth routes are working!"

# --- Forgot Password ---
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        # 🔹 Placeholder: implement actual reset email later
        flash("If that email exists, a password reset link has been sent.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")