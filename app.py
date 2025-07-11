import os
import logging
from contextlib import contextmanager
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash

# --- Local Imports ---
# Make sure these imports match the actual function names in your respective files
from genai_interface import query_chatbot
from registration import registration_bp
from chat_history import chat_bp
from db import create_tables, get_connection # Renamed for clarity

# --- App Initialization & Configuration ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO) # Add basic logging

# Securely configure the secret key
if 'FLASK_SECRET_KEY' in os.environ:
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')
else:
    logging.warning("FLASK_SECRET_KEY environment variable not set. Using a temporary key for development.")
    app.config['SECRET_KEY'] = os.urandom(24)

# Run table creation once at app startup
create_tables()

# Register Blueprints
app.register_blueprint(registration_bp)
app.register_blueprint(chat_bp)


# ==============================================================================
# REFACTORED: Database & Data Access Logic
# ==============================================================================

@contextmanager
def db_cursor():
    """
    A context manager to handle database connections and cursors automatically.
    This replaces the repetitive try...finally blocks.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        yield cursor # Provides the cursor to the 'with' block
        conn.commit() # Commits transaction if no exceptions were raised
    except Exception as e:
        logging.error(f"Database Error: {e}")
        if conn:
            conn.rollback() # Rollback on error
        # Re-raise the exception to be handled by the calling function if needed
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def db_get_chat_titles(user_id: int) -> list:
    """Fetches all chat titles for a given user."""
    with db_cursor() as cursor:
        cursor.execute("SELECT chat_id, title FROM chats WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        return cursor.fetchall()

def db_save_message(chat_id: int, sender: str, message: str):
    """Saves a single message to the database."""
    with db_cursor() as cursor:
        cursor.execute(
            "INSERT INTO messages (chat_id, sender, message) VALUES (%s, %s, %s)",
            (chat_id, sender, message)
        )

def db_create_new_chat(user_id: int, first_message: str) -> dict:
    """Creates a new chat record and returns its details."""
    # Simple logic to create a title from the first message
    title = (first_message[:40] + '...') if len(first_message) > 40 else first_message
    with db_cursor() as cursor:
        cursor.execute(
            "INSERT INTO chats (user_id, title) VALUES (%s, %s)",
            (user_id, title)
        )
        new_chat_id = cursor.lastrowid
        return {'chat_id': new_chat_id, 'title': title}
def db_rename_chat(user_id: int, chat_id: int, new_title: str):
    """Renames a specific chat for a given user."""
    with db_cursor() as cursor:
        # Check that your table is named 'chats' and columns are 'title', 'chat_id', 'user_id'
        cursor.execute(
            "UPDATE chats SET title = %s WHERE chat_id = %s AND user_id = %s",
            (new_title, chat_id, user_id)
        )

# ==============================================================================
# Login & Session Management
# ==============================================================================

@app.before_request
def require_login():
    """Checks user session before each request."""
    allowed_endpoints = ['registration.login', 'registration.signup', 'static']

    if 'user_id' in session:
        # If logged in, redirect away from login/signup
        if request.endpoint in ['registration.login', 'registration.signup']:
            flash("You are already logged in.", "info")
            return redirect(url_for('home'))
        return # User is logged in and accessing an allowed page

    # If not logged in, only allow access to specific endpoints
    if request.endpoint not in allowed_endpoints:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for('registration.login'))


# ==============================================================================
# Main Application Routes
# ==============================================================================

@app.route('/')
def home():
    """Renders the main chat interface."""
    user_id = session.get('user_id')
    try:
        # REFACTORED: Use the dedicated data access function
        chat_titles = db_get_chat_titles(user_id)
    except Exception as e:
        chat_titles = []
        flash("Could not load chat history. Please try again later.", "error")
        logging.error(f"Error fetching chat titles for user {user_id}: {e}")

    return render_template('index.html', chat_titles=chat_titles)


@app.route('/get-response', methods=['POST'])
def get_response():
    """Handles incoming messages, gets a bot reply, and saves the conversation."""
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({'response': 'Please enter a message.'}), 400

    user_id = session.get('user_id')
    active_chat_id = session.get('active_chat_id')
    new_chat_info = {}

    try:
        # REFACTORED: Centralized logic for creating new chats
        if not active_chat_id:
            new_chat_info = db_create_new_chat(user_id, user_input)
            active_chat_id = new_chat_info['chat_id']
            session['active_chat_id'] = active_chat_id

        # Get bot reply (this can be slow, so do it before DB writes if possible)
        reply = query_chatbot(user_input)

        # Save both messages
        db_save_message(active_chat_id, "user", user_input)
        db_save_message(active_chat_id, "assistant", reply)

        # REFACTORED: Send new chat info back to the frontend
        response_data = {'response': reply}
        if new_chat_info:
            response_data['new_chat'] = new_chat_info

        return jsonify(response_data)

    except Exception as e:
        logging.error(f"Error in get_response for user {user_id}: {e}")
        return jsonify({'response': 'An error occurred. Could not process your message.'}), 500
@app.route('/rename-chat', methods=['POST'])
def rename_chat():
    """Renames a chat title in the database."""
    data = request.get_json()
    chat_id = data.get('chat_id')
    new_title = data.get('new_title')
    user_id = session.get('user_id')

    if not all([chat_id, new_title, user_id]):
        return jsonify({'error': 'Missing data'}), 400

    try:
        db_rename_chat(user_id, chat_id, new_title)
        return jsonify({'success': True, 'message': 'Chat renamed successfully.'})
    except Exception as e:
        logging.error(f"Error renaming chat {chat_id} for user {user_id}: {e}")
        return jsonify({'error': 'Database error occurred.'}), 500

# --- Application Entry Point ---
if __name__ == '__main__':
    app.run(debug=True)