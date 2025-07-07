from flask import Blueprint, render_template, session, jsonify, request
from db import get_connection
from genai_interface import query_chatbot

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/')
def homepage():
    user_id = session.get('user_id')
    chat_titles = []
    if user_id:
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT chat_id, title FROM chats "
                "WHERE user_id=%s ORDER BY created_at DESC",
                (user_id,)
            )
            chat_titles = cursor.fetchall()
    return render_template('index.html', chat_titles=chat_titles)

@chat_bp.route('/new-chat', methods=['POST'])
def new_chat():
    # Clear any active chat on server. 
    # If user isn’t signed in, it's a no-op.
    session.pop('chat_id', None)
    return jsonify({'status': 'ok'})

@chat_bp.route('/set-active-chat', methods=['POST'])
def set_active_chat():
    data = request.get_json()
    session['chat_id'] = data.get('chat_id')
    return jsonify({'status': 'ok'})

@chat_bp.route('/load-chat/<int:chat_id>')
def load_chat(chat_id):
    db = get_connection()
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT sender, message FROM messages "
            "WHERE chat_id=%s ORDER BY timestamp ASC",
            (chat_id,)
        )
        messages = cursor.fetchall()
    return jsonify({'messages': messages})

@chat_bp.route('/new-message', methods=['POST'])
def new_message():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'status': 'error', 'message': 'Please enter a message.'}), 400

    user_id = session.get('user_id')
    # If not signed in, just call Gemini and return
    if not user_id:
        bot_response = query_chatbot(user_message)
        return jsonify({'status': 'ok', 'bot': bot_response})

    # Signed-in user: handle persistent history
    db = get_connection()
    with db.cursor() as cursor:
        chat_id = session.get('chat_id')
        new_chat = False
        title = None

        if not chat_id:
            # First message in a fresh chat → create a row
            if len(user_message) > 30:
                title = user_message[:30].rstrip() + '…'
            else:
                title = user_message

            cursor.execute(
                "INSERT INTO chats (user_id, title) VALUES (%s, %s)",
                (user_id, title)
            )
            chat_id = cursor.lastrowid
            session['chat_id'] = chat_id
            new_chat = True

        # Insert user's message
        cursor.execute(
            "INSERT INTO messages (chat_id, sender, message) "
            "VALUES (%s, 'user', %s)",
            (chat_id, user_message)
        )

        # Real bot reply
        bot_response = query_chatbot(user_message)

        # Save bot reply
        cursor.execute(
            "INSERT INTO messages (chat_id, sender, message) "
            "VALUES (%s, 'assistant', %s)",
            (chat_id, bot_response)
        )

        db.commit()

    return jsonify({
        'status': 'ok',
        'chat_id': chat_id,
        'bot': bot_response,
        'new_chat': new_chat,
        'title': title
    })
