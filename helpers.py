import requests
from urllib.parse import quote_plus
from functools import wraps
from flask import (
    Flask,
    render_template,
    redirect,
    session,
    request,
    jsonify
)
import openai
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

app = Flask(__name__)

# Define the OpenAI API base URL
OPENAI_API_BASE_URL = "https://api.openai.com/v1/"

def apology(message, code=400):
    """
    Render message as an apology to the user.

    Args:
        message (str): The apology message to display.
        code (int): The HTTP status code for the response.

    Returns:
        str: Rendered HTML apology page.
    """
    def escape(s):
        """
        Escape special characters in a string.

        Args:
            s (str): The input string.

        Returns:
            str: The escaped string.
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code

def login_required(f):
    """
    Decorate routes to require login.

    Args:
        f (function): The route function to decorate.

    Returns:
        function: The decorated route function.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def get_openai_api_key():
    """
    Retrieve the OpenAI API key from Azure Key Vault.

    Returns:
        str: The OpenAI API key.
    """
    # Azure Key Vault configuration
    key_vault_url = "https://gio.vault.azure.net/"
    secret_name = "OpenAIKey"

    # Create a SecretClient using DefaultAzureCredential
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=key_vault_url, credential=credential)

    try:
        # Retrieve the OpenAI API key from Azure Key Vault
        secret = client.get_secret(secret_name)

        # Return the OpenAI API key as a string
        return secret.value

    except Exception as e:
        print(f"Error while retrieving OpenAI API key from Azure Key Vault: {e}")
        return None

def lookup(symbol):
    try:
        # Your implementation for the lookup function goes here
        return None
    except (requests.RequestException, ValueError, KeyError):
        return None

def usd(value):
    return f"${value:,.2f}"

def generate_image(description, image_style, image_dimensions, **kwargs):
    """
    Generate an image using the OpenAI API based on the description, style, and dimensions.

    Args:
        description (str): The description of the image.
        image_style (str): The style to be applied to the image.
        image_dimensions (str): The dimensions of the image.
        kwargs (dict): Optional keyword arguments, including image_format and image_quality.

    Returns:
        str: URL of the generated image.
    """
    try:
        # Retrieve the OpenAI API key from Azure Key Vault
        openai_api_key = get_openai_api_key()

        if openai_api_key:
            # Configure the OpenAI API key
            openai.api_key = openai_api_key

            prompt = description

            # Add the style and dimensions to the prompt
            prompt += f", {image_style}, {image_dimensions}"

            # Check if image_format and image_quality are provided in kwargs
            if 'image_format' in kwargs:
                prompt += f", {kwargs['image_format']}"

            if 'image_quality' in kwargs:
                prompt += f", {kwargs['image_quality']}"

            response = openai.Image.create(
               model="dall-e-2",  # Specify the correct DALL·E model name
               prompt=prompt,
               n=1,
               size="1024x1024"  # Adjust as needed
            )

            # Extract the URL of the generated image
            image_url = response.data[0]['url']

            return image_url

    except Exception as e:
        print(f"Error in generate_image: {e}")
        return None

if __name__ == "__main__":
    app.run(debug=True)
