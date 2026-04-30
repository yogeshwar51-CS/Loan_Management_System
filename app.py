from flask import Flask, render_template, request, redirect, session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from db_config import get_cursor
from datetime import timedelta
import time

app = Flask(__name__)
app.secret_key = "super_secret_key"

app.permanent_session_lifetime = timedelta(minutes=10)

LOCK_TIME = 2  # minutes

def get_remaining(cursor, loan_id):
    cursor.execute("SELECT loan_amount FROM loans WHERE loan_id=%s", (loan_id,))
    loan_amount = float(cursor.fetchone()[0])

    cursor.execute("""
        SELECT IFNULL(SUM(amount_paid),0)
        FROM payments
        WHERE loan_id=%s
    """, (loan_id,))
    paid = float(cursor.fetchone()[0])

    return loan_amount, paid, (loan_amount - paid)


# =========================
# 🔐 SESSION HANDLING
# =========================
@app.before_request
def session_timeout():
    session.permanent = True



def admin_required():
    if 'admin_id' not in session:
        return redirect('/admin_login')
    return None

@app.route('/')
def home():
    return render_template('select_login.html', hide_nav=True)

# =========================
# 🔐 ADMIN LOGIN
# =========================
from werkzeug.security import check_password_hash
import time

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():

    MAX_ATTEMPTS = 3
    LOCK_TIME = 60  # seconds

    # 🔹 Initialize session values
    if 'attempts' not in session:
        session['attempts'] = 0

    if 'lock_time' not in session:
        session['lock_time'] = 0

    # 🔒 CHECK LOCK
    if session['lock_time'] > time.time():
        remaining = int(session['lock_time'] - time.time())
        flash(f"Too many attempts ❌ Locked for {remaining} seconds", "danger")
        return render_template('login.html')   # ⚠️ no redirect loop

    # 🔓 RESET AFTER LOCK EXPIRES
    if session['lock_time'] != 0 and session['lock_time'] <= time.time():
        session['attempts'] = 0
        session['lock_time'] = 0

    if request.method == 'POST':

        username = request.form.get('username')
        password = request.form.get('password')

        db, cursor = get_cursor()
        cursor.execute("SELECT * FROM admin WHERE username=%s", (username,))
        admin = cursor.fetchone()
        db.close()

        # ✅ SUCCESS LOGIN
        if admin:
            stored_password = admin[2]

            if stored_password and check_password_hash(stored_password, password):

                # 🔥 MAIN FIX
                session['admin'] = True
                session['admin_id'] = admin[0]
                session['admin_name'] = admin[1]

                session['attempts'] = 0
                session['lock_time'] = 0

                flash("Login Successful ✅", "success")
                return redirect('/admin')

        # ❌ FAILED LOGIN
        session['attempts'] += 1
        remaining = MAX_ATTEMPTS - session['attempts']

        if remaining <= 0:
            session['lock_time'] = time.time() + LOCK_TIME
            flash("Too many attempts ❌ Locked for 1 minute 🔒", "danger")
        else:
            flash(f"Invalid credentials ❌ Attempts left: {remaining}", "danger")

        return redirect('/admin_login')

    return render_template('login.html')


# =========================
# 🏠 ADMIN PANEL
# =========================
@app.route('/admin')
def admin_dashboard():
    check = admin_required()
    if check:
        return check

    db, cursor = get_cursor()

    # 🔹 TOTAL USERS
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # 🔹 TOTAL LOANS
    cursor.execute("SELECT COUNT(*) FROM loans")
    total_loans = cursor.fetchone()[0]

    # 🔹 TOTAL LOAN AMOUNT
    cursor.execute("SELECT IFNULL(SUM(loan_amount),0) FROM loans")
    total_amount = cursor.fetchone()[0]

    # 🔹 CLOSED LOANS (FULLY PAID)
    cursor.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT 
                l.loan_id,
                (l.loan_amount - IFNULL(SUM(p.amount_paid),0)) AS remaining
            FROM loans l
            LEFT JOIN payments p ON l.loan_id = p.loan_id
            GROUP BY l.loan_id
        ) AS t
        WHERE t.remaining <= 0
    """)
    closed_loans = cursor.fetchone()[0]

    # 🔹 ACTIVE / PENDING LOANS
    cursor.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT 
                l.loan_id,
                (l.loan_amount - IFNULL(SUM(p.amount_paid),0)) AS remaining
            FROM loans l
            LEFT JOIN payments p ON l.loan_id = p.loan_id
            GROUP BY l.loan_id
        ) AS t
        WHERE t.remaining > 0
    """)
    active_loans = cursor.fetchone()[0]

    db.close()

    return render_template(
        'dashboard.html',
        total_users=total_users,
        total_loans=total_loans,
        total_amount=total_amount,
        closed_loans=closed_loans,
        active_loans=active_loans
    )
# =========================
# 📊 DASHBOARD
# =========================
# @app.route('/dashboard')
# def dashboard():
#     check = admin_required()
#     if check:
#         return check
#     db, cursor = get_cursor()

#     cursor.execute("SELECT COUNT(*) FROM users")
#     total_users = cursor.fetchone()[0]

#     cursor.execute("SELECT COUNT(*) FROM loans")
#     total_loans = cursor.fetchone()[0]

#     cursor.execute("SELECT SUM(loan_amount) FROM loans")
#     total_amount = cursor.fetchone()[0] or 0
#     db.close()

#     return render_template(
#         'dashboard.html',
#         total_users=total_users,
#         total_loans=total_loans,
#         total_amount=total_amount
#     )


# =========================
# 👤 USERS
# =========================
@app.route('/add_user', methods=['GET','POST'])
def add_user():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        password = request.form.get('password')

        hashed = generate_password_hash(password)

        db, cursor = get_cursor()

        cursor.execute("""
            INSERT INTO users (name, email, phone, address, password)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, email, phone, address, hashed))

        db.commit()     # ✅ FIRST
        db.close()      # ✅ THEN CLOSE

        flash("User added successfully ✅", "success")
        return redirect('/view_users')   # ✅ correct route

    return render_template('add_user.html')

@app.route('/view_users')
def view_users():
    check = admin_required()
    if check:
        return check
    db, cursor = get_cursor()

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    db.close()

    return render_template('view_users.html', users=users)

@app.route('/edit_user/<int:user_id>', methods=['GET','POST'])
def edit_user(user_id):

    db, cursor = get_cursor()   # ✅ ADD THIS AT TOP

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')

        cursor.execute("""
            UPDATE users
            SET name=%s, email=%s, phone=%s, address=%s
            WHERE user_id=%s
        """, (name, email, phone, address, user_id))

        db.commit()
        db.close()

        flash("User updated successfully ✅", "success")
        return redirect('/view_users')   # ✅ FIXED

    # GET
    cursor.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
    user = cursor.fetchone()

    db.close()

    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    check = admin_required()
    if check:
        return check

    db, cursor = get_cursor()

    # ❌ prevent delete if user has loans
    cursor.execute("SELECT COUNT(*) FROM loans WHERE user_id=%s", (user_id,))
    if cursor.fetchone()[0] > 0:
        flash("User has loans ❌ Cannot delete", "danger")
        return redirect('/view_users')

    cursor.execute("DELETE FROM users WHERE user_id=%s", (user_id,))
    db.commit()
    db.close()

    flash("User deleted successfully ✅", "success")
    return redirect('/view_users')

@app.route('/user_dashboard')
def user_dashboard():

    if 'user_id' not in session:
        return redirect('/user_login')

    user_id = session['user_id']

    db, cursor = get_cursor()

    # 🔹 User name
    cursor.execute("SELECT name FROM users WHERE user_id=%s", (user_id,))
    name = cursor.fetchone()[0]

    # 🔹 Loans
    cursor.execute("""
        SELECT loan_id, loan_amount, interest_rate, status
        FROM loans
        WHERE user_id=%s
    """, (user_id,))
    loans = cursor.fetchall()

    # 🔹 Payments
    cursor.execute("""
        SELECT p.amount_paid, p.payment_method, p.payment_date
        FROM payments p
        JOIN loans l ON p.loan_id = l.loan_id
        WHERE l.user_id=%s
    """, (user_id,))
    payments = cursor.fetchall()

    db.close()

    return render_template(
        'user_dashboard.html',
        name=name,
        loans=loans,
        payments=payments
    )

# =========================
# 👤 USER login
# =========================

from werkzeug.security import check_password_hash
import time

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():

    MAX_ATTEMPTS = 3
    LOCK_TIME = 60  # seconds

    # 🔹 Initialize session values
    if 'user_attempts' not in session:
        session['user_attempts'] = 0

    if 'user_lock_time' not in session:
        session['user_lock_time'] = 0

    # 🔒 CHECK LOCK (FIXED — NO REDIRECT LOOP)
    if session['user_lock_time'] > time.time():
        remaining = int(session['user_lock_time'] - time.time())
        flash(f"Too many attempts ❌ Locked for {remaining} seconds", "danger")
        return render_template('user_login.html')   # ✅ FIX

    # 🔓 RESET AFTER TIME
    if session['user_lock_time'] != 0 and session['user_lock_time'] <= time.time():
        session['user_attempts'] = 0
        session['user_lock_time'] = 0

    if request.method == 'POST':

        email = request.form.get('email').strip()
        password = request.form.get('password').strip()

        db, cursor = get_cursor()

        cursor.execute("""
            SELECT user_id, name, password 
            FROM users 
            WHERE email=%s
        """, (email,))
        
        user = cursor.fetchone()
        db.close()

        # ✅ SUCCESS
        if user and check_password_hash(user[2], password):

            session['user_attempts'] = 0
            session['user_lock_time'] = 0

            session['user_id'] = user[0]
            session['user_name'] = user[1]

            flash("Login Successful ✅", "success")
            return redirect('/user_dashboard')

        # ❌ FAILED
        session['user_attempts'] += 1
        remaining = MAX_ATTEMPTS - session['user_attempts']

        if remaining > 0:
            flash(f"Invalid Credentials ❌ Attempts left: {remaining}", "danger")
        else:
            session['user_lock_time'] = time.time() + LOCK_TIME
            flash("Too many attempts ❌ Locked for 1 minute 🔒", "danger")

        return redirect('/user_login')

    return render_template('user_login.html')

@app.route('/user_apply_loan', methods=['GET','POST'])
def user_apply_loan():
    if 'user_id' not in session:
        return redirect('/user_login')

    if request.method == 'POST':
        user_id = session['user_id']
        amount = request.form.get('amount')
        interest = request.form.get('interest')
        time = request.form.get('time')

        db, cursor = get_cursor()

        cursor.execute("""
            INSERT INTO loans (user_id, loan_amount, interest_rate, time_years, status, start_date)
            VALUES (%s,%s,%s,%s,'Active',CURDATE())
        """, (user_id, amount, interest, time))

        db.commit()
        db.close()

        return redirect('/user_dashboard')

    return render_template('user_apply_loan.html')

@app.route('/user_make_payment', methods=['GET','POST'])
def user_make_payment():

    if 'user_id' not in session:
        return redirect('/user_login')

    user_id = session['user_id']
    db, cursor = get_cursor()

    # 🔹 LOANS WITH REAL REMAINING
    cursor.execute("""
        SELECT 
            l.loan_id,
            l.loan_amount,
            (l.loan_amount - IFNULL(SUM(p.amount_paid),0)) AS remaining
        FROM loans l
        LEFT JOIN payments p ON l.loan_id = p.loan_id
        WHERE l.user_id=%s
        GROUP BY l.loan_id
    """, (user_id,))
    loans = cursor.fetchall()

    # 🔹 PAYMENTS (for UI calc)
    cursor.execute("""
        SELECT loan_id, amount_paid
        FROM payments
        WHERE loan_id IN (
            SELECT loan_id FROM loans WHERE user_id=%s
        )
    """, (user_id,))
    payments = cursor.fetchall()

    # 🔹 POST
    if request.method == 'POST':
        loan_id = request.form.get('loan_id')
        amount = float(request.form.get('amount'))
        method = request.form.get('method')

        # 🔹 GET REAL REMAINING
        cursor.execute("""
            SELECT 
                l.loan_amount,
                IFNULL(SUM(p.amount_paid),0)
            FROM loans l
            LEFT JOIN payments p ON l.loan_id = p.loan_id
            WHERE l.loan_id=%s
            GROUP BY l.loan_id
        """, (loan_id,))
        row = cursor.fetchone()

        if not row:
            flash("Invalid loan ❌", "danger")
            return redirect('/user_make_payment')

        loan_amount = float(row[0])
        paid = float(row[1])
        remaining = loan_amount - paid

        # 🔥 BLOCK FULLY PAID
        if remaining <= 0:
            flash("Loan already fully paid ❌", "danger")
            return redirect('/user_make_payment')

        # 🔥 BLOCK OVERPAYMENT
        if amount > remaining:
            flash("Cannot pay more than remaining amount ❌", "danger")
            return redirect('/user_make_payment')

        # 🔹 INSERT
        cursor.execute("""
            INSERT INTO payments (loan_id, amount_paid, payment_method, payment_date)
            VALUES (%s,%s,%s,CURDATE())
        """, (loan_id, amount, method))

        db.commit()
        db.close()

        flash("Payment Successful 🎉", "payment_success")
        return redirect('/user_make_payment')

    db.close()

    return render_template(
        'user_make_payment.html',
        loans=loans,
        payments=payments
    )

@app.route('/user_emi', methods=['GET','POST'])
def user_emi():

    if 'user_id' not in session:
        return redirect('/user_login')

    emi = None

    if request.method == 'POST':
        P = float(request.form.get('amount'))
        R = float(request.form.get('rate')) / 100 / 12
        T = float(request.form.get('time')) * 12

        emi = (P * R * (1+R)**T) / ((1+R)**T - 1)

    return render_template('user_emi.html', emi=emi)

@app.route('/user_change_password', methods=['GET', 'POST'])
def user_change_password():
    if 'user_id' not in session:
        return redirect('/user_login')

    user_id = session['user_id']

    db, cursor = get_cursor()

    if request.method == 'POST':
        old = request.form.get('old_password')
        new = request.form.get('new_password')

        # 🔹 GET CURRENT PASSWORD
        cursor.execute("SELECT password FROM users WHERE user_id=%s", (user_id,))
        current = cursor.fetchone()[0]

        # 🔴 CHECK OLD PASSWORD
        if old != current:
            db.close()
            return render_template(
                'user_change_password.html',
                error="Old password is incorrect ❌"
            )

        # 🔹 UPDATE PASSWORD
        cursor.execute(
            "UPDATE users SET password=%s WHERE user_id=%s",
            (new, user_id)
        )
        db.commit()
        db.close()

        # ✅ SEND SUCCESS FLAG
        return render_template(
            'user_change_password.html',
            success=True
        )

    db.close()
    return render_template('user_change_password.html')

# =========================
# 💰 LOANS
# =========================
@app.route('/add_loan', methods=['GET','POST'])
def add_loan():

    db, cursor = get_cursor()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        amount = request.form.get('loan_amount')
        interest = request.form.get('interest_rate')
        years = request.form.get('time_years')

        cursor.execute("""
            INSERT INTO loans (user_id, loan_amount, interest_rate, time_years, start_date, status)
            VALUES (%s, %s, %s, %s, CURDATE(), 'Active')
        """, (user_id, amount, interest, years))

        db.commit()
        db.close()

        flash("Loan added successfully ✅", "success")
        return redirect('/view_loans')

    cursor.execute("SELECT user_id, name FROM users")
    users = cursor.fetchall()

    db.close()

    return render_template('add_loan.html', users=users)

@app.route('/edit_loan/<int:loan_id>', methods=['GET','POST'])
def edit_loan(loan_id):

    db, cursor = get_cursor()   # ✅ ALWAYS FIRST

    if request.method == 'POST':
        amount = request.form.get('loan_amount')
        interest = request.form.get('interest_rate')
        years = request.form.get('time_years')
        status = request.form.get('status')

        cursor.execute("""
            UPDATE loans
            SET loan_amount=%s, interest_rate=%s, time_years=%s, status=%s
            WHERE loan_id=%s
        """, (amount, interest, years, status, loan_id))

        db.commit()
        db.close()

        flash("Loan updated successfully ✅", "success")
        return redirect('/view_loans')

    # GET (load existing loan)
    cursor.execute("SELECT * FROM loans WHERE loan_id=%s", (loan_id,))
    loan = cursor.fetchone()

    db.close()

    return render_template('edit_loan.html', loan=loan)



@app.route('/delete_loan/<int:loan_id>')
def delete_loan(loan_id):
    check = admin_required()
    if check:
        return check

    db, cursor = get_cursor()

    # 🔍 Check if payments exist
    cursor.execute("SELECT COUNT(*) FROM payments WHERE loan_id=%s", (loan_id,))
    payment_count = cursor.fetchone()[0]

    if payment_count > 0:
        flash("Cannot delete ❌ Loan has payments", "danger")
        db.close()
        return redirect('/view_loans')

    # ✅ Delete loan
    cursor.execute("DELETE FROM loans WHERE loan_id=%s", (loan_id,))
    db.commit()
    db.close()

    flash("Loan deleted successfully ✅", "success")
    return redirect('/view_loans')

@app.route('/add_payment', methods=['GET', 'POST'])
def add_payment():
    check = admin_required()
    if check:
        return check

    db, cursor = get_cursor()

    try:
        # 🔹 USERS
        cursor.execute("SELECT user_id, name FROM users")
        users = cursor.fetchall()

        # 🔹 LOANS (WITH REAL REMAINING)
        cursor.execute("""
            SELECT 
                l.loan_id,
                l.user_id,
                l.loan_amount,
                IFNULL(SUM(p.amount_paid),0) AS paid,
                (l.loan_amount - IFNULL(SUM(p.amount_paid),0)) AS remaining
            FROM loans l
            LEFT JOIN payments p ON l.loan_id = p.loan_id
            GROUP BY l.loan_id
        """)
        loans = cursor.fetchall()

        # 🔹 PAYMENTS (for frontend)
        cursor.execute("SELECT loan_id, amount_paid FROM payments")
        payments = cursor.fetchall()

        # 🔹 HANDLE POST
        if request.method == 'POST':
            loan_id = request.form.get('loan_id')
            amount = request.form.get('amount')
            method = request.form.get('method')

            # 🔴 VALIDATION
            if not loan_id or not amount or not method:
                flash("All fields required ❌", "danger")
                return redirect('/add_payment')

            amount = float(amount)

            # 🔹 REAL-TIME FETCH
            cursor.execute("""
                SELECT 
                    l.loan_amount,
                    IFNULL(SUM(p.amount_paid),0) AS paid
                FROM loans l
                LEFT JOIN payments p ON l.loan_id = p.loan_id
                WHERE l.loan_id=%s
                GROUP BY l.loan_id
            """, (loan_id,))

            row = cursor.fetchone()

            if not row:
                flash("Invalid loan ❌", "danger")
                return redirect('/add_payment')

            loan_amount = float(row[0])
            paid = float(row[1])
            remaining = loan_amount - paid

            # 🔥 BLOCK FULLY PAID
            if remaining <= 0:
                flash("Loan already fully paid ❌", "danger")
                return redirect('/add_payment')

            # 🔥 BLOCK OVERPAYMENT
            if amount > remaining:
                flash("Payment exceeds remaining balance ❌", "danger")
                return redirect('/add_payment')

            # 🔹 INSERT PAYMENT
            cursor.execute("""
                INSERT INTO payments (loan_id, amount_paid, payment_method, payment_date)
                VALUES (%s, %s, %s, CURDATE())
            """, (loan_id, amount, method))

            # 🔥 RE-CALCULATE AFTER INSERT
            cursor.execute("""
                SELECT IFNULL(SUM(amount_paid),0)
                FROM payments
                WHERE loan_id=%s
            """, (loan_id,))
            updated_paid = float(cursor.fetchone()[0])

            # 🔥 OPTIONAL: AUTO CLOSE LOAN
            if updated_paid >= loan_amount:
                cursor.execute("""
                    UPDATE loans
                    SET status='Closed'
                    WHERE loan_id=%s
                """, (loan_id,))

            db.commit()

            flash("Payment Successful ✅", "payment_success")
            return redirect('/view_payments')

        # 🔹 GET REQUEST
        return render_template(
            'add_payment.html',
            users=users,
            loans=loans,
            payments=payments
        )

    except Exception as e:
        db.rollback()  # 🔥 IMPORTANT
        print("ERROR:", e)
        flash("Something went wrong ❌", "danger")
        return redirect('/add_payment')

    finally:
        db.close()

@app.route('/emi')
def emi():
    check = admin_required()
    if check:
        return check
    return render_template('emi.html')

@app.route('/view_loans')
def view_loans():
    check = admin_required()
    if check:
        return check

    db, cursor = get_cursor()

    cursor.execute("""
        SELECT 
            l.loan_id,
            u.name,
            l.loan_amount,
            l.interest_rate,
            l.status
        FROM loans l
        JOIN users u ON l.user_id = u.user_id
    """)

    loans = cursor.fetchall()
    db.close()

    return render_template('view_loans.html', loans=loans)


    
@app.route('/closed_loans')
def closed_loans():
    check = admin_required()
    if check:
        return check

    db, cursor = get_cursor()

    cursor.execute("""
        SELECT 
            l.loan_id,
            u.name,
            l.loan_amount,
            l.interest_rate,
            IFNULL(SUM(p.amount_paid),0) AS total_paid,
            (l.loan_amount - IFNULL(SUM(p.amount_paid),0)) AS remaining
        FROM loans l
        JOIN users u ON l.user_id = u.user_id
        LEFT JOIN payments p ON l.loan_id = p.loan_id
        GROUP BY l.loan_id
        HAVING remaining = 0
        ORDER BY l.loan_id DESC
    """)

    loans = cursor.fetchall()
    db.close()

    return render_template('closed_loans.html', loans=loans)

@app.route('/active_loans')
def active_loans():
    check = admin_required()
    if check:
        return check

    db, cursor = get_cursor()

    try:
        cursor.execute("""
            SELECT 
                l.loan_id,
                u.name,
                l.loan_amount,
                l.interest_rate,
                IFNULL(SUM(p.amount_paid),0) AS total_paid,
                (l.loan_amount - IFNULL(SUM(p.amount_paid),0)) AS remaining
            FROM loans l
            JOIN users u ON l.user_id = u.user_id
            LEFT JOIN payments p ON l.loan_id = p.loan_id
            GROUP BY l.loan_id
            HAVING remaining > 0
            ORDER BY remaining DESC
        """)

        loans = cursor.fetchall()

        return render_template('active_loans.html', loans=loans)

    except Exception as e:
        print("ERROR:", e)
        flash("Something went wrong ❌", "danger")
        return redirect('/admin')

    finally:
        db.close()
# =========================
# 🔐 ADMIN PASSWORD
# =========================
@app.route('/admin_change_password', methods=['GET', 'POST'])
def admin_change_password():
    check = admin_required()
    if check:
        return check

    if request.method == 'POST':
        old = request.form['old_password']
        new = request.form['new_password']
        confirm = request.form['confirm_password']
        db, cursor = get_cursor()

        cursor.execute("SELECT password FROM admin WHERE admin_id=%s", (session['admin_id'],))
        current = cursor.fetchone()[0]

        if not check_password_hash(current, old):
            flash("Old password incorrect ❌", "error")
            return redirect('/admin_change_password')

        if new != confirm:
            flash("Passwords do not match ❌", "error")
            return redirect('/admin_change_password')

        hashed = generate_password_hash(new)

        cursor.execute(
            "UPDATE admin SET password=%s WHERE admin_id=%s",
            (hashed, session['admin_id'])
        )
        db.commit()
        db.close()

        flash("Password updated successfully ✅", "success")
        return redirect('/dashboard')

    return render_template('admin_change_password.html')


# =========================
# 🔄 RESET USER PASSWORD
# =========================
@app.route('/admin_reset_user_password', methods=['GET','POST'])
def admin_reset_user_password():
    db, cursor = get_cursor()
    cursor.execute("SELECT user_id, name FROM users")
    users = cursor.fetchall()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_password = request.form.get('password')

        print("USER:", user_id)
        print("PASSWORD:", new_password)

        if not user_id or not new_password:
            flash("All fields required ❌", "error")
            return redirect(request.url)

        hashed = generate_password_hash(new_password)

        cursor.execute(
            "UPDATE users SET password=%s WHERE user_id=%s",
            (hashed, user_id)
        )
        db.commit()
        db.close()

        flash("Password reset successful ✅", "success")
        return redirect('/view_users')

    return render_template('admin_reset_password.html', users=users)


# =========================
# 🚪 LOGOUT
# =========================
# @app.route('/logout')
# def logout():
#     flash("Logged out successfully ✅", "success")  # ✅ FIRST
#     session.clear()                                # ✅ AFTER
#     return redirect('/')                # ✅ go to page that shows flash


# @app.route('/user_logout')
# def user_logout():
#     flash("Logged out successfully ✅", "success")
#     session.clear()
#     return redirect('/')
@app.route('/logout')
def logout():
    flash("Logged out successfully ✅", "success")
    session.clear()
    return redirect('/')
# =========================
# 🛡️ NO CACHE
# =========================
@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    return response

# =========================
# 💳 VIEW PAYMENTS
# =========================
@app.route('/view_payments')
def view_payments():
    check = admin_required()
    if check:
        return check

    db, cursor = get_cursor()

    cursor.execute("""
        SELECT 
            p.payment_id,
            u.name,
            l.loan_id,
            l.loan_amount,
            p.amount_paid,
            p.payment_method,
            p.payment_date
        FROM payments p
        JOIN loans l ON p.loan_id = l.loan_id
        JOIN users u ON l.user_id = u.user_id
        ORDER BY p.payment_id DESC
    """)

    payments = cursor.fetchall()

    db.close()

    return render_template('view_payments.html', payments=payments)

# =========================
# 📜 VIEW TRANSACTIONS
# =========================
@app.route('/view_transactions')
def view_transactions():
    check = admin_required()
    if check:
        return check
    db, cursor = get_cursor()

    cursor.execute("""

        SELECT 
            payments.payment_id,
            payments.loan_id,
            users.user_id,
            users.name,
            payments.amount_paid,
            payments.payment_method,
            'Credit' AS type,
            payments.payment_date AS trans_date

        FROM payments
        JOIN loans ON payments.loan_id = loans.loan_id
        JOIN users ON loans.user_id = users.user_id

        UNION ALL

        SELECT 
            loans.loan_id,
            loans.loan_id,
            users.user_id,
            users.name,
            loans.loan_amount,
            'Loan Given',
            'Debit',
            loans.start_date AS trans_date

        FROM loans
        JOIN users ON loans.user_id = users.user_id

        ORDER BY trans_date DESC
    """)

    transactions = cursor.fetchall()  # 🔥 MUST BE THERE
    db.close()  

    return render_template('view_transactions.html', transactions=transactions)



if __name__ == "__main__":
    app.run(debug=True)