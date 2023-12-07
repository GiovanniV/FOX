import os
import sqlite3
import secrets
from tempfile import mkdtemp
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    jsonify,
    current_app as app,
    url_for,
    send_from_directory,
    make_response,
)
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd, generate_image

# Configure application
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = mkdtemp()
Session(app)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_urlsafe(16))

# Function to get a database connection
def get_db_connection():
    conn = sqlite3.connect('finance.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, post-check=0, pre-check=0"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Routes
@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    return render_template("buy.html")

@app.route('/generate-image', methods=['POST'])
@login_required
def generate_image_route():
    try:
        # Extract data from form
        description = request.form.get("image_description")
        image_style = request.form.get("image_style")
        image_dimensions = request.form.get("image_dimensions")

        # Create a dictionary for optional parameters
        optional_params = {
            "image_format": request.form.get("image_format"),
            "image_quality": request.form.get("image_quality"),
        }

        # Call the generate_image function with required parameters and optional parameters as kwargs
        image_url = generate_image(description, image_style, image_dimensions, **optional_params)

        if image_url:
            # Generate a response with the image URL and set the content-disposition header for downloading
            response = make_response(jsonify({"image_url": image_url}))
            response.headers["Content-Disposition"] = f'attachment; filename=image.jpg'  # You can customize the filename here
            return response
        else:
            # Log the error and return an appropriate JSON response
            app.logger.error("Unable to generate image")
            return jsonify({"error": "Unable to generate image"}), 500
    except Exception as e:
        # Log the exception details for debugging
        app.logger.error(f"An unexpected error occurred: {e}")
        # Return an error message in a JSON response
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/api/image-styles', methods=['GET'])
def get_image_styles():
    image_styles = ["Style1", "Style2", "Style3"]  # Replace this with your actual data source
    return jsonify(image_styles)

@app.route('/static/generated_images/<filename>')
def serve_generated_image(filename):
    return send_from_directory('/Users/venegas/Desktop/fox/Foxfromgit/FOX/static/generated_images', filename)

@app.route('/images')
def images():
    return render_template('images.html')

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
    session.clear()
    return redirect("/")

from flask import render_template, request, flash, redirect, url_for
from helpers import login_required

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

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
