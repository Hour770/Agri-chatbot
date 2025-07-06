from flask import Flask, render_template, request, jsonify, session
from genai_interface import query_chatbot
from registration import registration_bp
from chat_history import chat_bp
from db import create_tables

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session


# Run table creation once at app startup
create_tables()

# Register Blueprints
app.register_blueprint(registration_bp)
app.register_blueprint(chat_bp)

@app.route('/get-response', methods=['POST'])
def get_response():
    user_input = request.json.get('message', '')
    if not user_input:
        return jsonify({'response': 'Please enter a message.'})

    reply = query_chatbot(user_input)

    # Optional: Save message to DB here (user_input and reply), linked to session['chat_id']
    return jsonify({'response': reply})

if __name__ == '__main__':
    app.run(debug=True)
