from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
import sqlite3
from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, NumberRange
from datetime import datetime
import os

shop = Blueprint("shop", __name__, template_folder="../templates/shop")

# Database path
shopfleetdb = '../greenwells-operations/greenwells_operations/instance/shopfleet.db'

def get_db_connection():
    conn = sqlite3.connect(shopfleetdb)
    conn.row_factory = sqlite3.Row
    return conn

# Routes
@shop.route('/shop')
def shop_home():
    conn = get_db_connection()
    try:
        products = conn.execute('SELECT * FROM Products WHERE status = "Not sold"').fetchall()
        categories = conn.execute('SELECT DISTINCT product_category FROM Products').fetchall()
    except sqlite3.OperationalError as e:
        flash('Database error: ' + str(e), 'danger')
        products = []
        categories = []
    finally:
        conn.close()
    
    # Use session-based cart
    cart = session.get("cart", [])
    total_price = sum(item['price'] * item.get('quantity', 1) for item in cart)
    
    return render_template('shop_home.html', products=products, categories=[c['product_category'] for c in categories], 
                         cart=cart, total_price=total_price)

@shop.route('/shop/category/<category>')
def shop_category(category):
    conn = get_db_connection()
    try:
        products = conn.execute('SELECT * FROM Products WHERE product_category = ? AND status = "Not sold"', (category,)).fetchall()
        categories = conn.execute('SELECT DISTINCT product_category FROM Products').fetchall()
    except sqlite3.OperationalError as e:
        flash('Database error: ' + str(e), 'danger')
        products = []
        categories = []
    finally:
        conn.close()
    
    # Use session-based cart
    cart = session.get("cart", [])
    total_price = sum(item['price'] * item.get('quantity', 1) for item in cart)
    
    return render_template('shop_home.html', products=products, categories=[c['product_category'] for c in categories], 
                         current_category=category, cart=cart, total_price=total_price)

@shop.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    conn = get_db_connection()
    try:
        product = conn.execute(
            'SELECT * FROM Products WHERE product_id = ? AND status = "Not sold"',
            (product_id,)
        ).fetchone()

        if not product:
            flash('Product not available.', 'danger')
            return redirect(url_for('shop.shop_home'))

        # read quantity from the submitted form, with safe fallback
        try:
            qty = int(request.form.get('quantity', 1))
        except (ValueError, TypeError):
            qty = 1
        # clamp quantity to a sensible range
        qty = max(1, min(qty, 100))

        # Use session cart for all users (both logged in and guests)
        cart = session.get("cart", [])

        # Check if product already in cart
        product_found = False
        for item in cart:
            if item["id"] == product_id:
                # add the requested qty to existing quantity
                item["quantity"] = item.get("quantity", 1) + qty
                product_found = True
                break

        # If not found, add new item with requested qty
        if not product_found:
            cart.append({
                "id": product['product_id'],
                "name": product['product_name'],
                "price": product['retail_price'],
                "quantity": qty
            })

        session["cart"] = cart
        session.modified = True
        flash(f'Added {qty} × {product["product_name"]} to cart!', 'success')

    except sqlite3.OperationalError as e:
        flash('Database error: ' + str(e), 'danger')
    finally:
        conn.close()

    return redirect(url_for('shop.shop_home'))


@shop.route('/cart')
def cart():
    # Check if user is authenticated to view cart
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty.', 'info')
        return redirect(url_for('shop.shop_home'))
    
    # Use session-based cart
    cart = session.get("cart", [])
    subtotal = sum(item['price'] * item.get('quantity', 1) for item in cart)
    tax = subtotal * 0.16  # Assuming 16% tax
    total = subtotal + tax
    
    return render_template('cart.html', cart=cart, subtotal=subtotal, tax=tax, total=total)

@shop.route('/cart/remove/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    # Remove from session cart
    cart = session.get("cart", [])
    # Filter out the item with the matching ID
    new_cart = []
    for item in cart:
        if item["id"] != item_id:
            new_cart.append(item)
    session["cart"] = new_cart
    session.modified = True
    flash('Item removed from cart.', 'success')
    
    return redirect(url_for('shop.cart'))

@shop.route('/cart/clear', methods=['POST'])
def clear_cart():
    # Clear session cart
    session.pop("cart", None)
    flash('Cart cleared.', 'success')
    
    return redirect(url_for('shop.shop_home'))

@shop.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get("cart", [])
    
    if not cart:
        flash('Your cart is empty.', 'danger')
        return redirect(url_for('shop.shop_home'))
    
    # Get user ID from current user
    user_id = getattr(current_user, 'id', None) or getattr(current_user, 'user_id', None)
    
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            
            # Get customer location from database
            customer_info = conn.execute("""
                SELECT location FROM Users WHERE user_id = ?
            """, (user_id,)).fetchone()
            
            customer_location = customer_info['location'] if customer_info else 'Unknown Location'
            
            # Create a detailed cart summary with product info for internal use
            cart_details = []
            
            # Get product details for each item in cart
            for item in cart:
                quantity = item.get('quantity', 1)
                
                # Get product location from database
                product_info = conn.execute("""
                    SELECT product_location FROM Products WHERE product_id = ?
                """, (item['id'],)).fetchone()
                
                location = product_info['product_location'] if product_info else 'Unknown'
                
                # Create detailed item info
                item_info = {
                    'id': item['id'],
                    'name': item['name'],
                    'quantity': quantity,
                    'location': location
                }
                cart_details.append(item_info)
            
            # Create detailed cart summary string for internal reference (store in cart status)
            cart_summary_items = []
            for item in cart_details:
                cart_summary_items.append(f"{item['name']} (ID: {item['id']}) x{item['quantity']} - Location: {item['location']}")
            
            cart_summary_str = "; ".join(cart_summary_items)
            
            # Create main cart entry
            cursor = conn.execute("""
                INSERT INTO Cart (product_id, user_id, status) 
                VALUES (?, ?, ?)
            """, (cart[0]['id'], user_id, f"Order_Items:{cart_summary_str}"))
            cart_id = cursor.lastrowid
            
            # Create order entry - SET product_destination to CUSTOMER LOCATION
            order_cursor = conn.execute("""
                INSERT INTO Orders (cart_id, employee_id, fleet_id, status, product_destination, product_arrival, otp, otp_timestamp, order_timestamp) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cart_id, 
                0,  # employee_id = 0 means not processed yet
                0,  # fleet_id = 0 means not assigned yet
                'Processing',  # Default status is Stage 1
                customer_location,  # SET TO CUSTOMER LOCATION - THIS IS THE DESTINATION
                0.0,  # product_arrival
                'No OTP',  # otp
                0.0,  # otp_timestamp
                datetime.now().timestamp()  # order_timestamp
            ))
            order_id = order_cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            # Clear session cart
            session.pop("cart", None)
            flash('Order placed successfully! Your order is now being processed.', 'success')
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            flash(f'Error processing order: {str(e)}', 'danger')
        
        return redirect(url_for('shop.shop_home'))
    
    # Display checkout page (GET request)
    subtotal = sum(item['price'] * item.get('quantity', 1) for item in cart)
    tax = subtotal * 0.16
    total = subtotal + tax
    
    order = {
        'items': [{'name': item['name'], 'price': item['price'], 'quantity': item.get('quantity', 1)} for item in cart],
        'subtotal': subtotal,
        'tax': tax,
        'total': total
    }
    
    return render_template('checkout.html', order=order)


@shop.route('/order_tracking/<int:order_id>', methods = ['POST'])
def order_tracking(order_id):
    # Mock order data (later this can come from DB)
    mock_order = {
        "id": order_id,
        "customer": "John Doe",
        "items": [
            {"name": "Engine Oil", "qty": 2, "price": 1500},
            {"name": "Brake Fluid", "qty": 1, "price": 800},
        ],
        "status": "Shipped"  # Change this to test: "Placed", "Processing", "Shipped", "Delivered"
    }

    return render_template("shop/order_tracking.html", order=mock_order)