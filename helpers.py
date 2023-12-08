import psycopg2
from flask import Flask, render_template, redirect, session
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import openai
from functools import wraps
import json


# Initialize the Flask app
app = Flask(__name__)

# Function to retrieve the OpenAI API key from Azure Key Vault
def get_openai_api_key():
    try:
        key_vault_url = "https://masterfox.vault.azure.net/"
        SECRET_NAME = "ok1"  # Replace with your secret name
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=key_vault_url, credential=credential)
        
        secret = client.get_secret(SECRET_NAME)
        return secret.value
    except Exception as e:
        print(f"Error while retrieving OpenAI API key: {e}")
        return None

# Function to establish a connection to the PostgreSQL database using Azure Key Vault
def get_db_connection():
    try:
        key_vault_url = "https://foxaimasterbd.vault.azure.net/"
        SECRET_NAME = "fox2"  # The name of your secret in Azure Key Vault
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=key_vault_url, credential=credential)

        # Retrieve the secret from Azure Key Vault
        secret = client.get_secret(SECRET_NAME)
        print(f"Retrieved secret: {secret}")

        # Parse the JSON string to get the database credentials
        db_credentials = json.loads(secret.value)
        print(f"Database credentials: {db_credentials}")

        # Use the credentials to establish the database connection
        connection = psycopg2.connect(
            user=db_credentials["user"],
            password=db_credentials["password"],
            host=db_credentials["host"],
            port=db_credentials["port"],
            database=db_credentials["database"],
        )

        return connection
    except Exception as e:
        print(f"Error while establishing database connection: {e}")
        return None

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# Function to render an apology message
def apology(message, code=400):
    return render_template("apology.html", top=code, bottom=message), code

# Function to generate an image using OpenAI's API and store it
def generate_image_and_store(openai_api_key, description, image_style, image_dimensions="1024x1024", image_quality="best", **kwargs):
    try:
        if not openai_api_key:
            print("OpenAI API key is missing or invalid")
            return None

        supported_sizes = ["1024x1024", "1024x1792", "1792x1024"]
        
        # Check if the specified size is supported
        if image_dimensions not in supported_sizes:
            print(f"Unsupported image size '{image_dimensions}'. Defaulting to '1024x1024'.")
            image_dimensions = "1024x1024"

        # Build the prompt for image generation
        prompt = f"Generate an image that is {image_dimensions} in size, Style: {image_style}, Description: {description}, Quality: {image_quality}"
        
        # Adding optional parameters to the prompt
        optional_params = ['image_format']
        for param in optional_params:
            if param in kwargs:
                prompt += f", {param.capitalize()}: {kwargs[param]}"

        client = openai.Client(api_key=openai_api_key)

        # Call the OpenAI API to generate the image
        response = client.images.generate(model="DALL·E 3", prompt=prompt, n=1, size=image_dimensions)
        print("Response from OpenAI API:")
        print(response)

        if response and 'data' in response and response['data']:
            image_url = response['data'][0].get('url')
            
            if image_url:
                # Store image URL in the database (implement your database logic here)
                return image_url
            else:
                print("No image URL found in response")
                return None
        else:
            print("Invalid or empty response from the API")
            return None

    except Exception as e:
        print(f"Error during image generation: {e}")
        return None

if __name__ == "__main__":
    app.run(debug=True)
