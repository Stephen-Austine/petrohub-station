from flask_login import UserMixin
import bcrypt
from extensions import db   # ✅ no circular import

class User(UserMixin, db.Model):
    __tablename__ = "Users"  # Match DB table

    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(50))
    lname = db.Column(db.String(50))
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15))
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(50), default="customer")

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

class Product(db.Model):
    __tablename__ = "Products"  # ✅ match actual DB table

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    price = db.Column(db.Float)
    stock = db.Column(db.Integer)

class Order(db.Model):
    __tablename__ = "Orders"  # ✅ match DB

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("Users.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("Products.id"))
    status = db.Column(db.String(50), default="Received")

class Fleet(db.Model):
    __tablename__ = "Fleet"  # ✅ match DB

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)         # e.g., "Truck A"
    reg_no = db.Column(db.String(30), unique=True)          # e.g., "KAA 123A"
    category = db.Column(db.String(50))                     # e.g., Tanker, Trailer, Small Truck
    status = db.Column(db.String(30), default="available")  # available, in transit, service

class FleetOrder(db.Model):
    __tablename__ = "FleetOrders"  # ✅ match DB

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("Users.id"))
    vehicle_type = db.Column(db.String(50))  # e.g., Tanker, Trailer, Small Truck
    quantity = db.Column(db.Integer)
    destination = db.Column(db.String(200))
    status = db.Column(db.String(50), default="Pending")  # Pending, Approved, Assigned, Completed
