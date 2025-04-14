from flask import Flask, render_template, redirect, url_for, request, session, flash
import string
from datetime import datetime
import random       # Used to simulate credit scores
app = Flask(__name__)           #Creates a Flask app instance
app.secret_key = 'W24022139'        # sets a secret key to enable sessions.

# ---------------------- Classes ----------------------

# Class to store user info
class User:
    def __init__(self, username, password):         # Constructor with username and password
        self.username = username
        self.password = password

    def to_dict(self):                  # Convert User object to dictionary for session storage
        return {"username": self.username, "password": self.password}

# Account class to manage bank accounts
class Account:
    def __init__(self, number, balance, code):
        self.number = number
        self.balance = balance
        self.code = code

    def withdraw(self, amount):      # Deducts amount if balance allows
        if self.balance >= amount:
            self.balance -= amount
            return True
        return False

    def to_dict(self):
        return {"number": self.number, "balance": self.balance, "code": self.code}

# Core banking system class
class BankSystem:
    def __init__(self):
        self.users = []         # List to store User objects

    # Validates strong password rules, found at stackoverflow website
    def is_strong_password(self, password):
        return all([
            len(password) >= 8,
            any(c in password for c in string.ascii_lowercase),
            any(c in password for c in string.ascii_uppercase),
            any(c in password for c in string.digits),
            any(c in password for c in string.punctuation)
        ])

    # Find user by username using generator expression
    def find_user(self, username):
        return next((user for user in self.users if user.username == username), None)

    # Adds new user if username not taken
    def register_user(self, username, password):
        if self.find_user(username):
            return False
        self.users.append(User(username, password))
        return True

bank = BankSystem()         # Create an instance of BankSystem

# ---------------------- Routes ----------------------

# Login route handles both GET and POST requests
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':    # Get form data from login submission
        username = request.form.get('username')
        password = request.form.get('password')

        user = bank.find_user(username)         # Find user in system
        if user and user.password == password:
            session['username'] = username
            session['customer_id'] = f"CUST-{username}"     # Optional ID
            session['accounts'] = [
                Account("12345678", 1500.50, "60-99-10").to_dict(),
                Account("87654321", 2500.75, "60-99-10").to_dict(),
            ]
            session['transactions'] = []        # Empty transactions list
            return redirect(url_for('home'))

        return render_template('login.jinja', error="Invalid username or password")

    return render_template('login.jinja')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if bank.find_user(username):        # Check if username is taken
            return render_template('register.jinja', error="Username already exists!")

        if not bank.is_strong_password(password):       # Password not strong
            return render_template(
                'register.jinja',
                error="Password must be at least 8 characters and contain:<br>"
                      "- At least one lowercase letter<br>"
                      "- At least one uppercase letter<br>"
                      "- At least one number<br>"
                      "- At least one special character (!@#$?& etc.)"
            )

        # Create new user and redirect to login
        bank.register_user(username, password)
        return redirect(url_for('login'))

    return render_template('register.jinja')        # Render registration form for GET requests


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        new_password = request.form.get('new_password')

        user = bank.find_user(username)     # Find user and validate new password
        if user:
            if bank.is_strong_password(new_password):
                user.password = new_password
                return render_template('forgot_password.jinja', success="Password updated successfully!")
            else:
                return render_template('forgot_password.jinja', error="New password is not strong enough!")

        return render_template('forgot_password.jinja', error="Account not found!")

    return render_template('forgot_password.jinja')


@app.route('/home')
def home():
    username = session.get('username')
    accounts = session.get('accounts')
    if not username or not accounts:
        return redirect(url_for('login'))
    # Prepare account data for display
    return render_template('home.jinja', accounts=[{
        "name": username,
        **account
    } for account in accounts])


@app.route('/account_summary')
def account_summary():
    if 'username' not in session:       # Require authentication
        return redirect(url_for('login'))
    # Get financial data from session
    accounts = session.get('accounts', [])
    transactions = session.get('transactions', [])

    return render_template("account_summary.jinja", accounts=accounts, transactions=transactions)


@app.route("/payments", methods=["GET", "POST"])
def payments():
    if "username" not in session:
        return redirect(url_for("login"))

    accounts = session.get("accounts", [])
    payees = session.get("payees", [])

    if request.method == "POST":        # Process payment form data
        from_account = request.form.get("from_account")
        selected_payee = request.form.get("payee")
        amount = request.form.get("amount")

        if not from_account or not selected_payee or not amount:        # Validate form completeness
            return render_template("payments.jinja", accounts=accounts, payees=payees,
                                   error="All fields are required.")

        try:
            amount = float(amount)          # Attempt to convert the entered amount to a float
            if amount <= 0:
                raise ValueError
        except ValueError:
            return render_template("payments.jinja", accounts=accounts, payees=payees,
                                   error="Enter a valid amount.")   # Show error message if invalid input

        for acc in accounts:        # Process payment if funds are available
            if acc['number'] == from_account:
                if acc['balance'] >= amount:
                    acc['balance'] -= amount    # Update account balance
                    # Record transaction
                    session['transactions'].append({
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'description': f"Paid to {selected_payee} from {from_account}",
                        'amount': amount
                    })
                    session.modified = True     # making sure that the session changes are saved
                    return render_template("payments.jinja", accounts=accounts, payees=payees,
                                           message="Payment successful.")
                else:
                    return render_template("payments.jinja", accounts=accounts, payees=payees,
                                           error="Insufficient funds.")

    return render_template("payments.jinja", accounts=accounts, payees=payees)


@app.route('/add_payee', methods=['GET', 'POST'])
def add_payee():
    if request.method == 'POST':
        payee_name = request.form.get('payee_name')
        bank = request.form.get('bank')
        account_number = request.form.get('account_number')
        sort_code = request.form.get('sort_code')

        if not all([payee_name, bank, account_number, sort_code]):
            flash("All fields are required.", "danger")
            return redirect(url_for('add_payee'))

        if 'payees' not in session: # Initialize payees list if not exists
            session['payees'] = []
        # Add new payee and save session
        session['payees'].append(payee_name)
        session.modified = True

        flash("New payee added successfully.", "success")       # 5sec flask notification
        return redirect(url_for('payments'))

    return render_template('add_payee.jinja')


@app.route('/apply', methods=['GET', 'POST'])
def apply():
    return render_template("apply.jinja")

import random

@app.route('/apply/loan')
def apply_loan():
    loan_options = [
        {"type": "Student Loan", "description": "Flexible repayment options for students."},
        {"type": "Home Loan", "description": "Low interest for your dream home."},
        {"type": "Auto Loan", "description": "Finance your new or used car easily."}
    ]

    credit_scores = [random.randint(500, 850) for _ in range(3)]

    messages = []
    for score in credit_scores:
        if score >= 700:
            messages.append(f"✅ Credit score {score}: Excellent – You are eligible.")
        elif score >= 600:
            messages.append(f"⚠️ Credit score {score}: Acceptable – Further checks needed.")
        else:
            messages.append(f"❌ Credit score {score}: Low – Not eligible.")

    logs = []
    for i in range(3):
        logs.append(f"System check #{i+1} passed")

    return render_template("apply_loan.jinja", loans=loan_options, messages=messages, logs=logs)

@app.route('/apply/mortgage')
def apply_mortgage():
    credit_scores = [random.randint(500, 850) for _ in range(3)]

    results = []
    for score in credit_scores:
        if score >= 750:
            results.append(f"🏡 Credit score {score}: Eligible for best mortgage rates.")
        elif score >= 650:
            results.append(f"🏠 Credit score {score}: Eligible with moderate rates.")
        else:
            results.append(f"🚫 Credit score {score}: Not eligible for mortgage.")

    status_log = []
    for step in range(3):
        status_log.append(f"Mortgage check {step+1}: OK")

    mortgage_types = [
        "Fixed Rate Mortgage",
        "Adjustable Rate Mortgage (ARM)",
        "Interest-Only Mortgage"
    ]

    return render_template("apply_mortgage.jinja", results=results, logs=status_log, types=mortgage_types)

@app.route('/apply/credit-card')
def apply_credit_card():
    card_types = [
        "Standard Credit Card",
        "Rewards Credit Card",
        "Secured Credit Card"
    ]

    approval_status = []
    credit_scores = [random.randint(500, 850) for _ in range(3)]
    for score in credit_scores:
        if score >= 720:
            approval_status.append(f"✅ Credit score {score}: Pre-approved for all cards.")
        elif score >= 600:
            approval_status.append(f"⚠️ Credit score {score}: Consider secured or student cards.")
        else:
            approval_status.append(f"❌ Credit score {score}: Credit card approval denied.")

    diagnostics = []
    for i in range(3):
        diagnostics.append(f"Card system diagnostic #{i+1}: OK")

    return render_template("apply_credit_card.jinja", cards=card_types, approvals=approval_status, diagnostics=diagnostics)

if __name__ == '__main__':
    app.run(port=8080, debug=True)


