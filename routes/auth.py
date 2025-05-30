from flask import render_template, redirect, url_for, session, request
from functools import wraps
from app import app, db, mail, serializer
from models import Admin
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify 
from flask_mail import Message 

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapper

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        success = request.args.get('success')
        return render_template('admin_login.html', success=success)
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    admin = Admin.query.filter_by(login=username).first()  # Ne filtrez plus par mot de passe

    if admin and check_password_hash(admin.password, password):  # Vérifiez le hash
        session['logged_in'] = True
        session.permanent = True
        return redirect(url_for('admin_page'))
    else:
        return render_template('admin_login.html', error="Identifiants incorrects")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email', '').strip()

    if not email:
        return jsonify({'success': False, 'message': 'Email requis'}), 400

    admin = Admin.query.filter_by(login=email).first()
    
    if not admin:
        return jsonify({'success': False, 'message': 'Email non trouvé'}), 404

    # Génération du token
    token = serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])
    reset_url = url_for('reset_password', token=token, _external=True)

    # Envoi d'email (exemple)
    try:
        msg = Message('Réinitialisation de mot de passe',
                      sender='no-reply@example.com',
                      recipients=[email])
        msg.body = f'Cliquez pour réinitialiser : {reset_url}'
        mail.send(msg)
        return jsonify({'success': True, 'message': 'Email envoyé avec instructions'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=3600 # 1h expiration
        )
    except:
        return render_template('Récupérer_Mdp.html', error='Lien invalide ou expiré')

    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirmed_password')

        if not password or not confirm:
            return render_template('Récupérer_Mdp.html', error='Tous les champs sont requis')

        if password != confirm:
            return render_template('Récupérer_Mdp.html', error='Les mots de passe ne correspondent pas')

        admin = Admin.query.filter_by(login=email).first()
        if admin:
            try:
                # Hashage du mot de passe
                admin.password = generate_password_hash(password)
                db.session.commit()
                return redirect(url_for('admin_login', success='Mot de passe réinitialisé avec succès'))
            except Exception as e:
                db.session.rollback()
                return render_template('Récupérer_Mdp.html', error='Erreur de base de données')
        
        return render_template('Récupérer_Mdp.html', error='Utilisateur non trouvé')

    return render_template('Récupérer_Mdp.html', token=token)

    
