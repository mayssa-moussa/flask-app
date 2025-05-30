from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)

class Gouvernorat(db.Model):
    __tablename__ = 'gouvernorats'
    id = db.Column(db.Integer, primary_key=True)
    gouvernorat = db.Column(db.String(100), nullable=False)
    date_upload = db.Column(db.Date, nullable=False)
    dossier_copie = db.Column(db.String(300), nullable=False)  # Renommé
    dossier_origine = db.Column(db.String(300), nullable=False)  # Nouvel attribut
    visible = db.Column(db.Boolean, default=True, nullable=False)
    def __repr__(self):
        return f'<Gouvernorat {self.gouvernorat} - {self.date_upload}>'