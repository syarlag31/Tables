from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User, db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('emailInput')
        password = request.form.get('passwordInput')
        
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in Sucessfully!', category="success")
                login_user(user, remember=True)
                return redirect(url_for('views.feed'))
            else:
                flash('Incorrect Password, try again.', category="error")
        else:
            flash('Email does not exist.', category="error")
    
    return render_template('Login.html', user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('views.landing'))

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "POST":
        email = request.form.get('emailInput')
        name = request.form.get('nameInput')
        handle = request.form.get('handleInput')
        password1 = request.form.get('passwordInput')
        password2 = request.form.get('confirmPasswordInput')
        
        user = User.query.filter_by(email=email).first()
        check_handle = User.query.filter_by(handle=handle).first()
        if user:
            flash('Email already exists.', category="error")
        elif check_handle:
            flash('Handle is already in use.', category="error")
        elif len(email) < 4:
            flash('Email must be greater than 4 characters.', category='error')
        elif len(name) < 5:
            flash('Names must be greater than 5 characters.', category='error')
        elif password1 != password2:
            flash('Password\'s do not match.')
        elif len(password1) < 7 or len(password2) < 7:
            flash('Passwords must be greater than 7 characters.', category='error')
        else:
            new_user = User(handle=handle, email=email, name=name, password=generate_password_hash(password1, method='sha256'))
            db.session.add(new_user)
            db.session.commit()
            flash('Account Created', category='success')
            login_user(new_user, remember=True)
            return redirect(url_for('views.feed'))
            
        
    return render_template('Signup.html', user=current_user)