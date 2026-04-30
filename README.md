# Loan_Management_System
Full-stack loan management system built with Python, Flask, and MySQL with features like EMI calculation and transaction tracking
## Important Note (Folder Structure)
Due to GitHub upload limitations, some files may appear with paths like:
templates/file.html instead of inside a visible folder.

However, while running the project locally, please make sure the folder structure is organized as follows:

loan-management-system/
│
├── static/
│   ├── images
│
├── templates/
│   ├── login.html
│   ├── base.html( css, js files)
│   ├── admin.html
│   ├── user pages
│   └── other HTML files
│
├── app.py
├── db_config.py

## How to Fix Structure After Download
After downloading or cloning the repository:

1. Create folders manually if not present:
   - Create a folder named `templates`
   - Create a folder named `static`

2. Move files accordingly:
   - Move all `templates/*.html` files into the `templates` folder
   - Move all `static/*` files into the `static` folder

3. Ensure the structure matches the one shown above before running the project.

## Software Requirements
Make sure the following are installed:

- Python (3.x)
- MySQL Server
- pip (Python package manager)

## Database Setup
- Create a MySQL database
- Update credentials in `db_config.py`
- Import required tables (if applicable)

## Running the Project (Quick Steps)
1. Install dependencies:
   pip install flask mysql-connector-python

2. Run the application:
   python app.py

3. Open in browser:
   http://127.0.0.1:5000/

## Troubleshooting
- If templates are not loading → check `templates/` folder structure
- If static files not working → check `static/` folder placement
- If database error → verify MySQL credentials in `db_config.py`
