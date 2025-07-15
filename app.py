from flask import Flask, render_template, request, jsonify
from chat import query_chatbot

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-response', methods=['POST'])
def get_response():
    user_input = request.json.get('message', '')
    if not user_input:
        return jsonify({'response': 'Please enter a message.'})
    reply = query_chatbot(user_input)
    return jsonify({'response': reply})

if __name__ == '__main__':
    app.run(debug=True)
