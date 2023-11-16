import os
import secrets
import sqlite3
import traceback
import logging
from flask import Flask, flash, redirect, render_template, request, session, jsonify, current_app as app
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd, generate_image
from flask import render_template, jsonify

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = mkdtemp()
Session(app)

# Function to get a database connection
def get_db_connection():
    conn = sqlite3.connect('finance.db')
    conn.row_factory = sqlite3.Row  # This allows you to access columns by name
    return conn

# Example usage of the connection to get table names
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
rows = cursor.fetchall()

# Print all table names
for row in rows:
    print(row['name'])

cursor.close()
conn.close()

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers[
        "Cache-Control"
    ] = "no-cache, no-store, must-revalidate, post-check=0, pre-check=0"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd



@app.route("/")
@login_required
def index():
    """Show portfolio of stocks and transaction history"""
    user_id = session["user_id"]

    # Open a database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Retrieve the user's portfolio of stocks
    cursor.execute("SELECT symbol, SUM(shares) as total_shares FROM transactions WHERE user_id = ? GROUP BY symbol HAVING total_shares > 0", (user_id,))
    portfolio = cursor.fetchall()

    # Prepare variables to hold the portfolio data and the grand total value
    holdings = []
    grand_total = 0

    # For each stock in the portfolio, look up the current price and calculate the total value
    for stock in portfolio:
        stock_info = lookup(stock["symbol"])
        if stock_info:
            total_value = stock_info["price"] * stock["total_shares"]
            holdings.append(
                {
                    "symbol": stock_info["symbol"],
                    "name": stock_info["name"],
                    "shares": stock["total_shares"],
                    "price": usd(stock_info["price"]),
                    "total": usd(total_value),
                }
            )
            grand_total += total_value
        else:
            # Handle the case where stock_info is None
            flash(f"Stock information for {stock['symbol']} could not be retrieved.", "warning")

    # Fetch transaction history for the user
    cursor.execute("SELECT symbol, shares, price, transacted FROM transactions WHERE user_id = ? ORDER BY transacted DESC", (user_id,))
    transactions = cursor.fetchall()

    # Modify transactions to include formatted price
    formatted_transactions = []
    for transaction in transactions:
        formatted_transaction = dict(transaction)
        formatted_transaction["price"] = usd(formatted_transaction["price"])
        formatted_transactions.append(formatted_transaction)

    # Get the current cash balance of the user
    cursor.execute("SELECT cash FROM users WHERE id = ?", (user_id,))
    cash = cursor.fetchone()["cash"]
    grand_total += cash

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Render the index page with the user's portfolio data, cash, grand total value, and transactions
    return render_template(
        "index.html",
        holdings=holdings,
        cash=usd(cash),
        grand_total=usd(grand_total),
        transactions=formatted_transactions,
    )




from flask import flash, redirect, render_template, request, session
from functools import wraps
import re  # Import regular expressions

import traceback



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol", "").upper()
        if not symbol or not re.match("^[A-Z.]{1,5}$", symbol):
            flash("Invalid or missing stock symbol.", "danger")
            return render_template("buy.html"), 400

        try:
            shares = int(request.form.get("shares"))
            if shares <= 0:
                raise ValueError
        except ValueError:
            flash("Shares must be a positive integer.", "danger")
            return render_template("buy.html"), 400

        stock = lookup(symbol)
        if stock is None:
            flash("Symbol not found.", "danger")
            return render_template("buy.html"), 400

        # Start SQLite transaction
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Check user's cash
            cursor.execute("SELECT cash FROM users WHERE id = ?", (session["user_id"],))
            user_cash = cursor.fetchone()["cash"]
            cost = stock["price"] * shares

            if cost > user_cash:
                flash("Not enough cash to complete the purchase.", "danger")
                return render_template("buy.html"), 400

            # Update user's cash
            cursor.execute("UPDATE users SET cash = cash - ? WHERE id = ?", (cost, session["user_id"]))

            # Record the transaction
            cursor.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)", (session["user_id"], symbol, shares, stock["price"]))

            # Commit transaction
            conn.commit()

        except Exception as e:
            # Rollback in case of error
            conn.rollback()
            print(f"Error processing purchase: {e}")
            flash("An error occurred while processing your purchase.", "danger")
            return render_template("buy.html"), 500
        finally:
            cursor.close()
            conn.close()

        flash("Purchase successful!", "success")
        return redirect(url_for("index"))
    else:
        return render_template("buy.html")

from flask import jsonify  # Import jsonify for JSON responses

@app.route("/generate-image", methods=["POST"])
@login_required
def generate_image_route():
    try:
        # Extract data from form
        description = request.form.get("image_description")

        # Call the generate_image function
        image_url = generate_image(description)

        if image_url:
            # Return the image URL in a JSON response
            return jsonify({"image_url": image_url})
        else:
            # Handle the error case
            app.logger.error("Error generating image")
            return jsonify({"error": "Error generating image"}), 500
    except Exception as e:
        app.logger.error(f"An unexpected error occurred: {e}")
        traceback.print_exc()  # Print the traceback for debugging
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route("/add_cash", methods=["GET", "POST"])
@login_required
def add_cash():
    """Add cash to account"""
    if request.method == "POST":
        # Ensure that amount is a positive number
        try:
            amount = float(request.form.get("amount"))
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError as e:
            # If there is a ValueError, return an apology with the error message
            return apology(str(e), 400)

        # Open a database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Perform the update on the user's cash balance
            cursor.execute("UPDATE users SET cash = cash + ? WHERE id = ?", (amount, session["user_id"]))
            conn.commit()

            # Verify that the database update affected exactly one row
            if cursor.rowcount < 1:
                return apology("Unable to add cash to account", 400)

            # If the update was successful, notify the user
            flash(f"${amount:.2f} added to your account!")
            return redirect("/")

        except Exception as e:
            conn.rollback()
            return apology(f"An error occurred: {e}", 500)
        finally:
            cursor.close()
            conn.close()
    else:
        # If method is GET, render the add_cash form
        return render_template("add_cash.html")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]

    # Initialize an empty list to hold transaction histories
    histories = []

    # Open a database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Fetch transaction history for the user
        cursor.execute("SELECT id, symbol, shares, price, transacted FROM transactions WHERE user_id = ? ORDER BY transacted DESC", (user_id,))
        transactions = cursor.fetchall()

        # Check if transactions were found
        if not transactions:
            flash("No transaction history found.")  # Flash a message to the user

        # Format transaction data
        for transaction in transactions:
            transaction_data = dict(transaction)
            transaction_data["price_formatted"] = usd(transaction_data["price"])
            transaction_data["total"] = transaction_data["shares"] * transaction_data["price"]
            transaction_data["total_formatted"] = usd(transaction_data["total"])
            transaction_data["transaction_date"] = transaction_data["transacted"]
            histories.append(transaction_data)

        # Return the history page with the transactions
        return render_template("history.html", transactions=histories)

    except Exception as e:
        print(f"An error occurred: {e}")  # This will print the exception to your console or logs
        flash("An error occurred while loading transaction history.")  # Flash a message to the user
        return redirect(url_for("index"))  # Redirect to index page or an error page if you prefer
    finally:
        cursor.close()
        conn.close()


@app.route("/login", methods=["GET", "POST"])
def login():
    # Forget any user_id
    session.clear()

    if request.method == "POST":
        # User reached route via POST (as by submitting a form via POST)
        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username:
            flash("Must provide username", "danger")
            return render_template("login.html")

        # Ensure password was submitted
        elif not password:
            flash("Must provide password", "danger")
            return render_template("login.html")

        # Open a database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Query database for username
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            rows = cursor.fetchall()

            # Ensure username exists and password is correct
            if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
                flash("Invalid username and/or password", "danger")
                return render_template("login.html")

            # Remember which user has logged in
            session["user_id"] = rows[0]["id"]

            # Redirect user to home page
            return redirect("/")
        finally:
            cursor.close()
            conn.close()
    else:
        # User reached route via GET
        return render_template("login.html")



@app.route("/logout")
def logout():
    # ... (implementation of the logout route as you provided)
    session.clear()
    return redirect("/")


from flask import render_template, request, flash, redirect, url_for
from helpers import lookup, usd, login_required


@app.route("/quote", methods=["GET", "POST"])
@login_required
def get_quote():
    if request.method == "POST":
        # Get the symbol from the form
        symbol = request.form.get("symbol").upper()

        # Check if the symbol is blank
        if not symbol:
            flash("Must provide a symbol", "error")
            return render_template("quote.html"), 400

        # Look up the current price of the stock
        stock = lookup(symbol)

        # Check if the symbol is invalid (stock is None)
        if stock is None:
            flash("Invalid symbol", "error")
            return render_template("quote.html"), 400

        # Display the stock price per share
        return render_template("quoted.html", stock=stock)
    else:
        # If method is GET, display the form to get a new quote
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("must provide username", 400)

        if not password:
            return apology("must provide password", 400)

        if password != confirmation:
            return apology("passwords do not match", 400)

        hash_pw = generate_password_hash(password)

        # Open a database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Insert the new user into the database
            cursor.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (username, hash_pw))
            conn.commit()

            # Retrieve the new user's id
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            new_user_id = cursor.fetchone()["id"]
            session["user_id"] = new_user_id

            flash("Registered!")
            return redirect("/")
        except sqlite3.IntegrityError:
            return apology("username already taken", 400)
        finally:
            cursor.close()
            conn.close()
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]

    if request.method == "POST":
        # Ensure symbol was submitted
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("must provide symbol", 400)

        # Convert symbol to uppercase to maintain consistency
        symbol = symbol.upper()

        # Ensure number of shares was submitted and is a positive integer
        try:
            shares_to_sell = int(request.form.get("shares"))
            if shares_to_sell <= 0:
                raise ValueError("Shares must be a positive integer")
        except ValueError:
            return apology("Shares must be a positive integer", 400)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Query database for the user's shares of that stock
            cursor.execute("SELECT SUM(shares) as total_shares FROM transactions WHERE user_id = ? AND symbol = ? GROUP BY symbol", (user_id, symbol))
            user_shares_result = cursor.fetchone()
            user_shares = user_shares_result['total_shares'] if user_shares_result else 0

            if user_shares < shares_to_sell:
                return apology("not enough shares", 400)

            # Get current stock price
            stock = lookup(symbol)
            if stock is None:
                return apology("Invalid Symbol", 400)

            # Calculate the revenue from selling the shares
            revenue = shares_to_sell * stock["price"]

            # Update the user's cash by adding the revenue from selling the shares
            cursor.execute("UPDATE users SET cash = cash + ? WHERE id = ?", (revenue, user_id))

            # Insert the transaction (as a negative number of shares)
            cursor.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)", (user_id, symbol, -shares_to_sell, stock["price"]))

            # Commit the transaction
            conn.commit()

        except sqlite3.Error as e:
            conn.rollback()
            return apology(f"Transaction failed: {e}", 400)
        finally:
            cursor.close()
            conn.close()

        # Notify the user of a successful sale
        flash(f"Sold {shares_to_sell} shares of {symbol}")
        return redirect("/")
    else:
        # User reached the route via GET
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0", (user_id,))
        symbols = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template("sell.html", symbols=[stock["symbol"] for stock in symbols])





# Only if your app runs with app.run(), not typically used in production
if __name__ == "__main__":
    app.run()


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500


# Make sure to use a secure and unique secret key in production
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_urlsafe(16))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
