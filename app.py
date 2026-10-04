from flask import Flask, render_template, request, redirect, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "expense-tracker-secret-key"


# Database connection
def get_db_connection():
    connection = sqlite3.connect("expense.db")
    connection.row_factory = sqlite3.Row
    return connection


# Home page
@app.route("/")
def home():
    connection = get_db_connection()

    expenses = connection.execute(
        "SELECT * FROM expenses ORDER BY id DESC"
    ).fetchall()

    connection.close()

    return render_template("index.html", expenses=expenses)
# About
@app.route("/about")
def about():
    return render_template("about.html")

# Add expense
@app.route("/add", methods=["GET", "POST"])
def add_expense():

    # User must be logged in
    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/")

    if request.method == "POST":

        title = request.form["title"].strip()
        amount = request.form["amount"]
        category = request.form["category"]
        date = request.form["date"]

        connection = get_db_connection()

        connection.execute(
            """
            INSERT INTO expenses
            (user_id, title, amount, category, date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                title,
                amount,
                category,
                date
            )
        )

        connection.commit()
        connection.close()

        flash("Expense added successfully!")

        return redirect("/dashboard")

    return render_template("add_expense.html")

# ==========================================
# REGISTER
# ==========================================

@app.route("/register", methods=["POST"])
def register():

    name = request.form["name"].strip()
    email = request.form["email"].strip().lower()
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]


    # Check password
    if password != confirm_password:

        flash("Passwords do not match.")

        return redirect("/")


    # Check password length
    if len(password) < 6:

        flash("Password must be at least 6 characters.")

        return redirect("/")


    connection = get_db_connection()


    # Check existing email
    existing_user = connection.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    ).fetchone()


    if existing_user:

        connection.close()

        flash("An account with this email already exists.")

        return redirect("/")


    # Hash password
    hashed_password = generate_password_hash(password)


    # Insert user
    connection.execute(
        """
        INSERT INTO users (name, email, password)
        VALUES (?, ?, ?)
        """,
        (name, email, hashed_password)
    )


    connection.commit()
    connection.close()


    flash("Account created successfully! You can now login.")

    return redirect("/")

@app.route("/login", methods=["POST"])
def login():

    email = request.form["email"].strip().lower()
    password = request.form["password"]

    connection = get_db_connection()

    user = connection.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    connection.close()

    if not user:
        flash("Invalid email or password.")
        return redirect("/")

    if not check_password_hash(user["password"], password):
        flash("Invalid email or password.")
        return redirect("/")

    # Create login session
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]

    flash("Login successful! Welcome back.")

    return redirect("/dashboard")
# Dashboard
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/")

    connection = get_db_connection()

    # User's expenses
    expenses = connection.execute(
        """
        SELECT *
        FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        """,
        (session["user_id"],)
    ).fetchall()


    # Total expenses
    total_expenses = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()[0]


    # Expense transaction count
    transaction_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM expenses
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()[0]


    # Total income
    total_income = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM incomes
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()[0]

       # ---------------- INCOMES ----------------

    incomes = connection.execute(
        """
        SELECT *
        FROM incomes
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    total_income = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM incomes
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()[0]


    # Balance
    balance = total_income - total_expenses


    connection.close()


    return render_template(
    "dashboard.html",
    expenses=expenses,
    total_expenses=total_expenses,
    transaction_count=transaction_count,
    incomes= incomes,
    total_income=total_income,
    balance=balance
)

@app.route("/edit-expense/<int:expense_id>", methods=["POST"])
def edit_expense(expense_id):

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/")

    title = request.form["title"].strip()
    amount = request.form["amount"]
    category = request.form["category"]
    date = request.form["date"]

    connection = get_db_connection()

    # Make sure this expense belongs to logged-in user
    expense = connection.execute(
        """
        SELECT id
        FROM expenses
        WHERE id = ? AND user_id = ?
        """,
        (expense_id, session["user_id"])
    ).fetchone()

    if not expense:
        connection.close()

        flash("Expense not found.")
        return redirect("/dashboard")


    connection.execute(
        """
        UPDATE expenses
        SET title = ?,
            amount = ?,
            category = ?,
            date = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            title,
            amount,
            category,
            date,
            expense_id,
            session["user_id"]
        )
    )

    connection.commit()
    connection.close()

    flash("Expense updated successfully!")

    return redirect("/dashboard")

@app.route("/delete-expense/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/")

    connection = get_db_connection()

    # Check that this expense belongs to the logged-in user
    expense = connection.execute(
        """
        SELECT id
        FROM expenses
        WHERE id = ? AND user_id = ?
        """,
        (expense_id, session["user_id"])
    ).fetchone()

    if not expense:
        connection.close()

        flash("Expense not found.")
        return redirect("/dashboard")

    connection.execute(
        """
        DELETE FROM expenses
        WHERE id = ? AND user_id = ?
        """,
        (expense_id, session["user_id"])
    )

    connection.commit()
    connection.close()

    flash("Expense deleted successfully!")

    return redirect("/dashboard")

#logout
@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.")

    return redirect("/")


@app.route("/add-income", methods=["POST"])
def add_income():
    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/")

    title = request.form.get("title", "").strip()
    amount = request.form.get("amount", "").strip()
    source = request.form.get("source", "").strip()
    date = request.form.get("date", "").strip()

    print("----- INCOME DATA -----")
    print("User ID:", session.get("user_id"))
    print("Title:", title)
    print("Amount:", amount)
    print("Source:", source)
    print("Date:", date)

    try:
        connection = get_db_connection()

        connection.execute(
            """
            INSERT INTO incomes
            (user_id, title, amount, source, date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                title,
                amount,
                source,
                date
            )
        )

        connection.commit()

        # Check whether row was actually inserted
        inserted_id = connection.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        print("Income inserted ID:", inserted_id)

        connection.close()

        flash("Income added successfully!")
        return redirect("/dashboard")

    except Exception as error:
        print("----- INCOME ERROR -----")
        print(error)

        if "connection" in locals():
            connection.close()

        flash("Income could not be added: " + str(error))
        return redirect("/dashboard")

@app.route("/incomes")
def incomes():
    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/")

    connection = get_db_connection()

    income_list = connection.execute(
        """
        SELECT *
        FROM incomes
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    total_income = connection.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM incomes
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()[0]

    connection.close()

    return render_template(
        "incomes.html",
        incomes=income_list,
        total_income=total_income
    )

@app.route("/edit-income/<int:income_id>", methods=["POST"])
def edit_income(income_id):

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/")

    title = request.form["title"].strip()
    amount = request.form["amount"]
    source = request.form["source"]
    date = request.form["date"]

    connection = get_db_connection()

    income = connection.execute(
        """
        SELECT id
        FROM incomes
        WHERE id = ? AND user_id = ?
        """,
        (income_id, session["user_id"])
    ).fetchone()

    if not income:
        connection.close()
        flash("Income not found.")
        return redirect("/dashboard")

    connection.execute(
        """
        UPDATE incomes
        SET title = ?,
            amount = ?,
            source = ?,
            date = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            title,
            amount,
            source,
            date,
            income_id,
            session["user_id"]
        )
    )

    connection.commit()
    connection.close()

    flash("Income updated successfully!")
    return redirect("/dashboard")


@app.route("/delete-income/<int:income_id>", methods=["POST"])
def delete_income(income_id):

    if "user_id" not in session:
        flash("Please login first.")
        return redirect("/")

    connection = get_db_connection()

    income = connection.execute(
        """
        SELECT id
        FROM incomes
        WHERE id = ? AND user_id = ?
        """,
        (income_id, session["user_id"])
    ).fetchone()

    if not income:
        connection.close()
        flash("Income not found.")
        return redirect("/dashboard")

    connection.execute(
        """
        DELETE FROM incomes
        WHERE id = ? AND user_id = ?
        """,
        (income_id, session["user_id"])
    )

    connection.commit()
    connection.close()

    flash("Income deleted successfully!")
    return redirect("/dashboard")







if __name__ == "__main__":
    app.run(debug=True)