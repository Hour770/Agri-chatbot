import logging
from flask import Blueprint, render_template, session, jsonify, request
# Assuming these are set up as in previous examples
from db import get_connection # Or your refactored db_cursor
from genai_interface import query_chatbot

# It's better to name the blueprint something descriptive
chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/')
def homepage():
    """Renders the main page with chat history."""
    user_id = session.get('user_id')
    chat_titles = []
    if user_id:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT chat_id, title FROM chats WHERE user_id=%s ORDER BY created_at DESC",
                (user_id,)
            )
            chat_titles = cursor.fetchall()
    return render_template('index.html', chat_titles=chat_titles)


@chat_bp.route('/new-chat', methods=['POST'])
def new_chat():
    """Clears the active chat ID from the session."""
    # CHANGED: Using consistent session key 'active_chat_id'
    session.pop('active_chat_id', None)
    return jsonify({'status': 'ok'})


@chat_bp.route('/set-active-chat', methods=['POST'])
def set_active_chat():
    """Sets the currently active chat in the user's session."""
    data = request.get_json()
    # CHANGED: Using consistent session key 'active_chat_id'
    session['active_chat_id'] = data.get('chat_id')
    return jsonify({'status': 'ok'})


@chat_bp.route('/load-chat/<int:chat_id>')
def load_chat(chat_id):
    """Loads all messages for a given chat ID, with a security check."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    db = get_connection()
    with db.cursor() as cursor:
        # ADDED: Security check to ensure the user owns the chat they are trying to load.
        cursor.execute(
            """
            SELECT m.sender, m.message FROM messages m
            JOIN chats c ON m.chat_id = c.chat_id
            WHERE m.chat_id=%s AND c.user_id=%s
            ORDER BY m.timestamp ASC
            """,
            (chat_id, user_id)
        )
        messages = cursor.fetchall()
    return jsonify({'messages': messages})


# CORRECTED: Route now matches the frontend's fetch call
@chat_bp.route('/get-response', methods=['POST'])
def get_response():
    """Handles a user message, gets a bot response, and saves to the database."""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Please enter a message.'}), 400

    user_id = session.get('user_id')
    if not user_id:
        # Handle non-logged-in users gracefully
        bot_response = query_chatbot(user_message)
        return jsonify({'response': bot_response})

    # Signed-in user: handle persistent history
    db = get_connection()
    with db.cursor() as cursor:
        # CHANGED: Using consistent session key 'active_chat_id'
        active_chat_id = session.get('active_chat_id')
        new_chat_info = None

        if not active_chat_id:
            # First message in a fresh chat -> create a row
            title = (user_message[:40] + '…') if len(user_message) > 40 else user_message
            cursor.execute(
                "INSERT INTO chats (user_id, title) VALUES (%s, %s)",
                (user_id, title)
            )
            active_chat_id = cursor.lastrowid
            session['active_chat_id'] = active_chat_id
            # CORRECTED: Create the object the frontend expects
            new_chat_info = {'chat_id': active_chat_id, 'title': title}

        # Insert user's message
        cursor.execute(
            "INSERT INTO messages (chat_id, sender, message) VALUES (%s, %s, %s)",
            (active_chat_id, 'user', user_message)
        )

        # Real bot reply
        bot_response = query_chatbot(user_message)

        # Save bot reply
        cursor.execute(
            "INSERT INTO messages (chat_id, sender, message) VALUES (%s, %s, %s)",
            (active_chat_id, 'assistant', bot_response)
        )

        db.commit()

    # CORRECTED: The JSON response now has the correct structure for the frontend
    response_data = {'response': bot_response}
    if new_chat_info:
        response_data['new_chat'] = new_chat_info

    return jsonify(response_data)