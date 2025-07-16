from flask import Blueprint, render_template, request, redirect, url_for, session, flash
# Assuming you have a db connection function in your db.py
from db import get_connection

# For secure password hashing
from werkzeug.security import generate_password_hash, check_password_hash

# Create a Blueprint for registration-related routes
registration_bp = Blueprint('registration', __name__)

@registration_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    Handles user registration.
    - GET: Displays the signup form.
    - POST: Processes the signup form submission.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Hash the password before storing it for security
        password_hash = generate_password_hash(password)

        conn = None
        cursor = None
        try:
            conn = get_connection()
            # Cursor created from get_connection() will be a DictCursor
            cursor = conn.cursor() 

            # 1. Check if username already exists in the database
            # Ensure 'user_id' matches your database schema's primary key column name
            cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                flash("Username already taken. Please choose a different one.", "error")
                return render_template('signup.html') # Re-render signup page with error message
            
            # 2. If username does not exist, proceed with inserting the new user
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash))
            conn.commit() # Commit the transaction to save changes to the database

            # Set session variables for the newly signed-up user to log them in automatically
            session['logged_in'] = True
            session['username'] = username
            # Get the ID of the newly inserted row (the user_id)
            session['user_id'] = cursor.lastrowid 

            flash("Account created successfully! You are now logged in.", "success")
            return redirect(url_for('home')) # Redirect to the main chat page (index.html)

        except Exception as e:
            # If an error occurs, rollback any pending database changes
            if conn: # Ensure connection exists before trying to rollback
                conn.rollback() 
            print(f"Error during signup: {e}")
            flash("An error occurred during signup. Please try again.", "error")
            return render_template('signup.html') # Re-render signup page with generic error

        finally:
            # Ensure database cursor and connection are closed in all cases
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # For GET requests, simply render the signup form
    return render_template('signup.html')


@registration_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login.
    - GET: Displays the login form.
    - POST: Processes the login form submission.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor() # DictCursor is set in get_connection()

            # Retrieve user data, including user_id and hashed password
            # Ensure column names match your database schema ('user_id', 'username', 'password_hash')
            cursor.execute("SELECT user_id, username, password_hash FROM users WHERE username = %s", (username,))
            user = cursor.fetchone() # Fetch the user record (as a dictionary)

            # Check if user exists and if the provided password matches the stored hash
            if user and check_password_hash(user['password_hash'], password):
                # If authentication is successful, set session variables
                session['logged_in'] = True
                session['username'] = user['username']
                session['user_id'] = user['user_id'] # Store user_id in session
                
                flash(f"Welcome back, {username}!", "success")
                return redirect(url_for('home')) # Redirect to the main chat page
            else:
                flash("Invalid username or password.", "error")
                return render_template('login.html') # Re-render login page with error

        except Exception as e:
            print(f"Error during login: {e}")
            flash("An error occurred during login. Please try again.", "error")
            return render_template('login.html') # Re-render login page with generic error

        finally:
            # Ensure database cursor and connection are closed
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # For GET requests, simply render the login form
    return render_template('login.html')

@registration_bp.route('/logout')
def logout():
    """
    Logs out the current user by clearing session variables.
    """
    session.pop('logged_in', None)  # Remove the 'logged_in' flag
    session.pop('username', None)   # Remove the username
    session.pop('user_id', None)    # Remove the user_id
    flash("You have been logged out.", "info")
    return redirect(url_for('registration.login')) # Redirect to the login page after logout