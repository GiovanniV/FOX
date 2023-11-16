import requests
from urllib.parse import quote_plus
from functools import wraps
from flask import render_template, redirect, session
import openai



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


def lookup(symbol):
    """
    Look up a stock quote for a given symbol.

    Args:
        symbol (str): The stock symbol to look up.

    Returns:
        dict: A dictionary containing stock information (name, price, symbol) or None if lookup fails.
    """
    try:
        url = f"https://cloud.iexapis.com/stable/stock/{quote_plus(symbol)}/quote?token=pk_7a8da2c5244547f7a5f7f1bca588e8c5"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return {
            "name": data["companyName"],
            "price": data["latestPrice"],
            "symbol": data["symbol"],
        }
    except (requests.RequestException, ValueError, KeyError):
        return None


def usd(value):
    """
    Format a value as USD.

    Args:
        value (float): The value to format.

    Returns:
        str: The formatted value as a string in USD currency format.
    """
    return f"${value:,.2f}"

def generate_image(description, styles=None, dimensions=None):
    """
    Generate an image using the OpenAI API based on the description, styles, and dimensions.

    Args:
        description (str): The description of the image.
        styles (str, optional): The styles to be applied to the image.
        dimensions (str, optional): The dimensions of the image.

    Returns:
        str: URL of the generated image.
    """
    try:
        openai.api_key = "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"

        prompt = description
        if styles:
            prompt += f", {styles}"
        if dimensions:
            prompt += f", {dimensions}"

        response = openai.Image.create(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024"  # Adjust as needed
        )
        return response.data[0]['url']  # Assuming the API returns a direct link to the image

    except Exception as e:
        print(f"Error in generate_image: {e}")
        return None