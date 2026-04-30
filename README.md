# Loan Management System

Full-stack loan management system built using Python, Flask, and MySQL with features like EMI calculation and transaction tracking.

## Features
- User Management
- Loan Creation and Tracking
- EMI Calculation
- Payment Tracking
- Admin Dashboard

## Technologies Used
- Python
- Flask
- MySQL
- HTML, CSS

## Project Structure
loan-management-system/
│
├── static/          # Contains images,
├── templates/       # HTML templates (login, admin, user pages)(*base.html contain  CSS, JS files)
├── app.py           # Main Flask application
├── db_config.py     # Database configuration

## Software Requirements
Make sure the following are installed:

- Python (3.x)
- MySQL Server
- pip (Python package manager)

## Database Setup
- Create a MySQL database
- Update credentials in `db_config.py`
- Ensure required tables are created

## How to Run
1. Install dependencies:
   pip install flask mysql-connector-python

2. Run the application:
   python app.py

3. Open in browser:
   http://127.0.0.1:5000/

## Troubleshooting
- If templates are not loading → verify `templates/` folder
- If static files are not loading → verify `static/` folder
- If database error → check MySQL credentials in `db_config.py`

## Author
Yogeshwar Udayagiri
