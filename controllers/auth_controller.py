from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from database.database_helper import get_user_by_username, get_user_by_email, create_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template('register.html')
            
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('register.html')
            
        if get_user_by_username(username):
            flash("Username already exists.", "danger")
            return render_template('register.html')
            
        if get_user_by_email(email):
            flash("Email address already registered.", "danger")
            return render_template('register.html')
            
        try:
            user = create_user(username, email, password)
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f"An error occurred during registration: {str(e)}", "danger")
            
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False
        
        user = get_user_by_username(username)
        
        if not user or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return render_template('login.html')
            
        login_user(user, remember=remember)
        next_page = request.args.get('next')
        flash(f"Welcome back, {user.username}!", "success")
        return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
