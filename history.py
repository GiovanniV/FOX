from flask import Flask, Blueprint, render_template, session, redirect, url_for, Response
from functools import wraps
import requests
import psycopg2
import json  # Add this import for JSON handling
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from helpers import login_required, get_openai_api_key, get_db_connection

app = Flask(__name__)
user_images = Blueprint('user_images', __name__)


def remove_unavailable_images(cursor, user_id):
    cursor.execute("SELECT id, image_url FROM images WHERE user_id = %s", (user_id,))
    rows = cursor.fetchall()

    for row in rows:
        image_id, image_url = row
        response = requests.head(image_url, timeout=5)

        if response.status_code != 200:
            cursor.execute("DELETE FROM images WHERE id = %s", (image_id,))

@user_images.route('/history')
@login_required
def display_history():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check and remove unavailable images
    remove_unavailable_images(cursor, user_id)

    cursor.execute("SELECT image_url FROM images WHERE user_id = %s ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()

    user_images_list = [(row[0], "Image") for row in rows]

    cursor.close()
    conn.close()

    return render_template('history.html', images=user_images_list)

@user_images.route('/download_image/<path:image_url>')
def download_image(image_url):
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            image_format = 'JPEG' if response.content.startswith(b'\xff\xd8') else 'PNG'
            file_extension = 'jpg' if image_format.lower() == 'jpeg' else image_format.lower()
            attachment_filename = f"downloaded_image.{file_extension}"
            return Response(
                response.content,
                content_type=f'image/{file_extension}',
                headers={"Content-Disposition": f"attachment; filename={attachment_filename}"}
            )
        else:
            return f"Failed to download image. Status code: {response.status_code}", 500
    except Exception as e:
        print(f"Error: {e}")
        return "Error downloading the image", 500

app.register_blueprint(user_images, url_prefix='/images')

if __name__ == '__main__':
    app.run(debug=True)
