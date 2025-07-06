from flask import Blueprint, render_template, request, redirect, session
from db import get_connection

registration_bp = Blueprint('registration', __name__)

@registration_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password))
            db.commit()
        return redirect('/login')
    return render_template('signup.html')

@registration_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username=%s AND password_hash=%s", (username, password))
            user = cursor.fetchone()
            if user:
                session['username'] = user['username']
                session['user_id'] = user['user_id']
                return redirect('/')
    return render_template('login.html')

@registration_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/')
