from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Resume(db.Model):
    """Resume model to store uploaded resume information"""
    __tablename__ = 'resumes'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Analysis results stored as JSON
    raw_text = db.Column(db.Text)
    word_count = db.Column(db.Integer)
    page_count = db.Column(db.Integer)
    contact_info = db.Column(db.JSON)
    skills = db.Column(db.JSON)  # List of skills
    experience_count = db.Column(db.Integer)
    education_found = db.Column(db.Boolean, default=False)
    score = db.Column(db.Integer)
    suggestions = db.Column(db.JSON)  # List of suggestions

    # Relationship with User
    user = db.relationship('User', backref=db.backref('resumes', lazy=True))

    def __repr__(self):
        return f'<Resume {self.filename}>'

    def to_dict(self):
        """Convert resume object to dictionary for API responses"""
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'analysis_date': self.analysis_date.isoformat() if self.analysis_date else None,
            'raw_text': self.raw_text,
            'word_count': self.word_count,
            'page_count': self.page_count,
            'contact_info': self.contact_info,
            'skills': self.skills,
            'experience_count': self.experience_count,
            'education_found': self.education_found,
            'score': self.score,
            'suggestions': self.suggestions
        }