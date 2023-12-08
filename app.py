import os
import secrets
from tempfile import mkdtemp  # Added import for mkdtemp
import logging
import openai
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from flask import Flask, request, redirect, url_for, render_template, session, flash
from werkzeug.utils import secure_filename
from flask import Flask, flash, redirect, render_template, request, session, jsonify, url_for, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash 
from flask_session import Session
from werkzeug.utils import secure_filename
from helpers import login_required, get_openai_api_key, get_db_connection
from flask import Flask, request, send_file
import psycopg2
from history import download_image
import re
from history import user_images
import json
  

# Create the app instance
app = Flask(__name__)


# Configure application
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = mkdtemp()
Session(app)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_urlsafe(16))

# Configure logging
logging.basicConfig(level=logging.DEBUG)


# Set the OpenAI API key using the function
api_key = get_openai_api_key()

if api_key:
    openai.api_key = api_key
else:
    # Handle the case where the API key retrieval fails
    print("API key not found or retrieval failed.")

# Register the user_images Blueprint
app.register_blueprint(user_images)

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, post-check=0, pre-check=0"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.template_filter('usd')
def usd_filter(value):
    # Implement currency formatting logic here
    # Example: return f"${value:.2f}"
    pass

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
        user_id = session.get("user_id")
        description = request.form.get("image_description")
        image_style = request.form.get("image_style")
        context = request.form.get("image_context", "").strip()
        mood = request.form.get("image_mood", "").strip()
        color_scheme = request.form.get("image_color", "").strip()
        image_dimensions = request.form.get("image_dimensions", "1024x1024")

        optional_params = {
            "image_format": request.form.get("image_format"),
            "image_quality": request.form.get("image_quality")
        }

        if not description or not image_style:
            return jsonify({"error": "Missing required arguments"}), 400

        api_key = get_openai_api_key()
        if not api_key:
            logging.error("Failed to retrieve OpenAI API key")
            return jsonify({"error": "Failed to retrieve OpenAI API key"}), 500

        # Constructing the prompt
        prompt = f"Generate a {image_style} image"
        if description:
         prompt += f". Description: {description}"
        if context:
         prompt += f", set in {context}"
        if image_dimensions:
         prompt += f" of {image_dimensions} pixels in size"
        if color_scheme:
         prompt += f", with a color scheme of {color_scheme}"

        logging.debug(f"OpenAI Prompt: {prompt}")

        # Dynamically setting the size parameter
        supported_sizes = ["1024x1024", "1024x1792", "1792x1024"]
        size_param = image_dimensions if image_dimensions in supported_sizes else "1024x1024"

        response = openai.Image.create(prompt=prompt, n=1, size=size_param)
        logging.debug(f"OpenAI API Response: {response}")

        # Processing the response
        if response and 'data' in response and response['data']:
            image_url = response['data'][0].get('url')
            # Store image information in the database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO images (user_id, description, style, dimensions, format, quality, image_url) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (user_id, description, image_style, image_dimensions, optional_params.get('image_format'), optional_params.get('image_quality'), image_url)
            )
            conn.commit()
            cursor.close()
            conn.close()

            # Return JSON response with the image URL
            return jsonify({"image_url": image_url}), 200
        else:
            logging.error("No image data found in response or error occurred")
            return jsonify({"error": "An error occurred during image generation. Please try again later."}), 500

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500



# New route to fetch image styles
@app.route('/api/image-styles', methods=['GET'])
def fetch_image_styles():
    image_styles = ["Style1", "Style2", "Style3"]  # Modify this list with actual styles
    return jsonify(image_styles)

# Route to serve images by filename
@app.route('/serve-image/<filename>')
def serve_image(filename):
    try:
        # Connect to the database
        connection = get_db_connection()

        # Query the database to fetch image data by filename
        cursor = connection.cursor()
        cursor.execute("SELECT image_data FROM images WHERE filename = %s", (filename,))
        image_data = cursor.fetchone()

        if image_data:
            # Serve the image data as a response
            return send_file(
                image_data[0],
                mimetype='image/jpeg'  # Adjust the mimetype based on your image format
            )
        else:
            return "Image not found", 404
    except Exception as e:
        return str(e), 500
    finally:
        cursor.close()
        connection.close()


# Route for the account page
@app.route('/account', methods=['GET'])
@login_required
def account():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Retrieve user data from the database
    cursor.execute("SELECT id, username, email FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user_data:
        flash("User not found", "danger")
        return redirect(url_for("login"))

    user = {
        "id": user_data[0],
        "username": user_data[1],
        "email": user_data[2],
    }
    return render_template('account.html', user=user)


@app.route('/images')
@login_required  # Ensure the user is logged in
def display_images():
    # Fetch user-specific images from the database
    user_id = session["user_id"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM images WHERE user_id = %s", (user_id,))
    user_images = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('images.html', images=user_images)

@app.route("/create")
@login_required  # If you want this page to be accessible only after logging in
def create():
    return render_template("create.html")

# Function to interact with the chatbot
def get_chatbot_response(user_input):
    api_key = get_openai_api_key()
    openai.api_key = api_key
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Replace with your preferred model
        messages=[{"role": "user", "content": user_input}]
    )
    return response.choices[0].message.content

# Route to handle chatbot requests
@app.route('/chatbot', methods=['POST'])
@login_required
def chatbot():
    try:
        data = request.get_json()
        user_input = data.get('content_request')  # Ensure this key matches the JavaScript request
        if not user_input:
            return jsonify({"error": "No input provided"}), 400

        chatbot_response = get_chatbot_response(user_input)
        return jsonify({"generated_content": chatbot_response})  # Key to match with JavaScript fetch
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Helper function to validate email
def is_email_valid(email):
    """Check if the email is in a valid format."""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# Helper function to validate password strength
def is_password_strong(password):
    """Check if the password is strong."""
    if len(password) < 8:
        return False
    if not re.search("[a-z]", password):
        return False
    if not re.search("[A-Z]", password):
        return False
    if not re.search("[0-9]", password):
        return False
    if not re.search("[_@$]", password):
        return False
    return True


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Username and password are required", "danger")
            return render_template("login.html")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            return redirect(url_for("index"))
        else:
            flash("Invalid username and/or password", "danger")
            return render_template("login.html")
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not all([first_name, last_name, email, username, password, confirmation]):
            flash("All fields are required", "danger")
            return render_template("register.html")

        if password != confirmation:
            flash("Passwords do not match", "danger")
            return render_template("register.html")

        if not is_email_valid(email):
            flash("Invalid email address", "danger")
            return render_template("register.html")

        if not is_password_strong(password):
            flash("Password is not strong enough", "danger")
            return render_template("register.html")

        hash_pw = generate_password_hash(password)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (first_name, last_name, email, username, password_hash) VALUES (%s, %s, %s, %s, %s)",
                (first_name, last_name, email, username, hash_pw)
            )
            conn.commit()
            cursor.close()
            conn.close()

            flash("Registered successfully!", "success")
            return redirect(url_for("login"))
        except psycopg2.IntegrityError:
            flash("Username already taken", "danger")
            return render_template("register.html")
        except Exception as e:
            flash(f"An error occurred: {e}", "danger")
            return render_template("register.html")
    else:
        return render_template("register.html")
        
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        user_id = session.get("user_id")
        
        if not user_id:
            return redirect(url_for("login"))

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()

        if result and check_password_hash(result[0], current_password):
            if new_password == confirm_password:
                # Update the user's password
                hashed_password = generate_password_hash(new_password)
                cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s",
                               (hashed_password, user_id))
                conn.commit()

                # Flash a success message
                flash('Password changed successfully.', 'success')
                
                # Log out the user after changing the password
                session.pop('user_id', None)
                session.pop('password', None)
                
                cursor.close()
                conn.close()
                
                return redirect(url_for('login'))
            else:
                flash('New password and confirm password do not match.', 'danger')
        else:
            flash('Current password is incorrect.', 'danger')

        cursor.close()
        conn.close()

    # Retrieve user data from the database (you can reuse the account route's code)
    user = get_user_data(user_id)
    
    return render_template('account.html', user=user)

# Helper function to retrieve user data from the database
def get_user_data(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, profile_image FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user_data:
        flash("User not found", "danger")
        return None

    return {
        "id": user_data[0],
        "username": user_data[1],
        "email": user_data[2],
        "profile_image": user_data[3],
    }

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)