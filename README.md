# PetroHub Station

PetroHub Station is a Flask-based business management and ordering platform for a petroleum distribution operation. The application supports customer ordering, employee and fleet management, gas refill requests, product inventory flows, and role-based access for internal staff.

The project is organized around a modular Flask app with blueprint-based routes, SQLite database access, login/role handling, and templated web pages for different business areas.

## Overview

This system is designed to cover multiple operational areas:

- Customer storefront and cart checkout
- Product catalog and order tracking
- Fleet booking and vehicle assignment
- Gas refill order intake
- Employee authentication and role-based access
- Bulk order management across operational departments

## Features

### Customer-facing features
- User signup and login
- OTP-based verification flow for staff login
- Product catalog browsing by category
- Session-based shopping cart
- Checkout and order creation workflow
- Fleet request form for customer transport bookings
- Gas refill order submission
- Order tracking views

### Administrative and operational features
- Role-based authorization for different users and staff types
- Dashboard views for staff and management
- Fleet management workflows
- Product management views
- Bulk order management
- Order status tracking and assignment logic
- Employee records and access control

### Technical features
- Flask application structure with blueprints
- SQLite persistence layer
- Flask-Login session handling
- Form validation via WTForms
- Template-based UI rendering with Jinja2
- Modular route organization for different business domains

## Tech Stack

- Python 3
- Flask
- Flask-Login
- Flask-WTF
- WTForms
- SQLite3
- bcrypt
- Jinja2 templates

## Project Structure

```text
petrohub-station/
├── README.md
├── dbcreation.py
├── shopfleetorg.sql
├── sql.py
├── petrohub_station/
│   ├── app.py
│   ├── config.py
│   ├── decorators.py
│   ├── extensions.py
│   ├── forms.py
│   ├── forms_fleet.py
│   ├── models.py
│   ├── patch_db.py
│   ├── testping.py
│   ├── user_object.py
│   ├── utils.py
│   ├── instance/
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── employees.py
│   │   ├── fleet.py
│   │   ├── gasrefill.py
│   │   └── shop.py
│   └── templates/
│       ├── base.html
│       ├── base2.html
│       ├── auth/
│       ├── fleet/
│       ├── gasrefill/
│       └── shop/
└── ...
```

## Core Application Entry Points

- `petrohub_station/app.py` – main Flask app and role-based dashboard logic
- `petrohub_station/routes/` – modular blueprint routes for auth, shop, fleet, and refill operations
- `dbcreation.py` – creates and initializes the SQLite database schema
- `shopfleetorg.sql` – SQL schema dump/reference file
- `petrohub_station/templates/` – frontend templates for pages, dashboards, and workflow screens

## Database Setup

This project uses SQLite. The database schema is initialized in `dbcreation.py` and includes tables such as:

- `Users`
- `Employees`
- `Products`
- `Cart`
- `Orders`
- `Fleet`
- `Reviews`
- `GasRefillOrders`
- `FleetOrders`
- `FleetOrderAssignments`
- `BulkOrders`

### Initialize the database

From the project root:

```bash
python3 dbcreation.py
```

This creates a SQLite database named `shopfleet.db` in the current working directory unless the code is adjusted to point elsewhere.

> Important: some route modules and the main app contain hardcoded database paths. If your local environment differs from the repository layout, update those paths before running the app.

## Installation

1. Clone the project.
2. Open a terminal in the project directory.
3. Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

4. Install the required packages:

```bash
pip install Flask Flask-Login Flask-WTF WTForms bcrypt
```

If you use other modules already present in the codebase, you may also need:

```bash
pip install flask_sqlalchemy
```

## Running the App

You can start the app using either of these approaches.

### Option 1: direct app execution

```bash
cd petrohub-station
python3 petrohub_station/app.py
```

### Option 2: Flask CLI

```bash
cd petrohub-station
export FLASK_APP=petrohub_station.app
flask run
```

Then open:

```text
http://127.0.0.1:5000/
```

## Authentication and Access Model

The app uses Flask-Login and custom role logic to drive access control. User and employee records are loaded through `UserObject` and the login manager in `petrohub_station/app.py`.

The role checks are implemented through a custom `role_required` decorator and can be used to protect pages by role name such as:

- `Admin`
- `FleetManager`
- `Driver`
- `Productmanager`
- `Customerservice`
- `Financer`

## Routes and Modules

### Auth
- `/signup`
- `/login`
- `/logout`
- OTP verification flow

### Shop
- `/shop`
- `/shop/category/<category>`
- `/cart`
- `/checkout`

### Fleet
- `/fleetordering`
- `/fleetorders`

### Gas refill
- Gas refill request and tracking pages are defined in the route modules and templates.

### Internal dashboards
- Staff dashboards and management screens are served through the blueprint modules and template folders.

## Important Notes

### Hardcoded database paths
The codebase contains several hardcoded SQLite paths to a folder layout that may not match this repository exactly. A few examples include paths such as:

- `greenwells_operations/instance/shopfleet.db`
- `../greenwells-operations/greenwells_operations/instance/shopfleet.db`
- `../../greenwells_operations/instance/shopfleet.db`

If the database does not load, make sure to align those paths with your working directory and actual database file location.

### Current development status
This project appears to be an internal/business application prototype rather than a polished production-ready SaaS app. It includes custom logic for a specific domain workflow and may require a bit of cleanup if it is being re-used in a new environment.

### Security considerations
The codebase includes email OTP login behavior and a hardcoded secret key in `petrohub_station/app.py`:

```python
app.config['SECRET_KEY'] = 'greenwells_secret'
```

This is acceptable for local development, but it should be replaced with an environment variable or secure secret in production.

## Common Development Commands

```bash
# activate environment
source .venv/bin/activate

# start app
python3 petrohub_station/app.py

# or run with flask CLI
export FLASK_APP=petrohub_station.app
flask run --debug
```

## Recommended Next Steps

- Standardize database configuration into a single environment-based setup
- Replace hardcoded paths and secrets with environment variables
- Add `.env` support and configuration management
- Document API flows and workflow logic for each department
- Add tests for authentication, checkout, and fleet request flows
- Clean up duplicate code and route naming inconsistencies

## License

This project does not currently show an explicit license file in the repository. If you are publishing or extending the project, add a license before distribution.

## Summary

PetroHub Station is a Flask-based operational management system for a petroleum business, covering product sales, fleet requests, gas refill orders, and staff management. It is a useful starting point for a multi-role logistics and commerce platform, with room for improved configuration, database portability, and production hardening.
