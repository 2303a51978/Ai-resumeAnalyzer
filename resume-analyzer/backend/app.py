from flask import Flask, request, jsonify, redirect, url_for, flash, render_template_string, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo
import os
import sqlite3
import traceback
from werkzeug.utils import secure_filename
from analyzer import analyze_resume
from models import db, Resume, User
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.config['CORS_HEADERS'] = 'Content-Type'

# Authentication configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for API simplicity

# Database configuration
_db_uri = os.getenv('DATABASE_URL', 'sqlite:///instance/resumes.db')
_db_path = None
if _db_uri.startswith('sqlite:///'):
    _db_path = _db_uri.replace('sqlite:///', '', 1)
    if not os.path.isabs(_db_path):
        _db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), _db_path))
        _db_uri = f"sqlite:///{_db_path.replace('\\', '/')}"
else:
    # Not a SQLite URI, leave it unchanged.
    _db_uri = _db_uri

if _db_path:
    os.makedirs(os.path.dirname(_db_path), exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = _db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.unauthorized_handler
def unauthorized():
    """Return JSON for API requests and redirect for browser page requests."""
    if request.path.startswith('/analyze') or request.path.startswith('/resumes') or request.path.startswith('/stats') or request.path.startswith('/auth/status'):
        return jsonify({'error': 'Authentication required'}), 401
    return redirect(url_for('login', next=request.path))

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 10 * 1024 * 1024))  # 10MB default

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# WTForms for registration and login
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=150)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')


def get_sqlite_db_path():
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not db_uri.startswith('sqlite:///'):
        return None
    db_path = db_uri.replace('sqlite:///', '', 1)
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(__file__), db_path)
    return db_path


def upgrade_sqlite_schema():
    db_path = get_sqlite_db_path()
    if not db_path:
        return

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if not os.path.exists(db_path):
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(resumes)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'user_id' not in columns:
            print('[INFO] Upgrading resume table schema to add user_id')
            cursor.execute('ALTER TABLE resumes ADD COLUMN user_id INTEGER')
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARNING] SQLite schema upgrade failed: {e}")


def create_tables():
    """Create database tables"""
    with app.app_context():
        upgrade_sqlite_schema()
        db.create_all()
        print("Database tables created successfully!")


# Create tables on first run
with app.app_context():
    try:
        upgrade_sqlite_schema()
        db.create_all()
        print("[INFO] Database tables verified/created")
    except Exception as e:
        print(f"[ERROR] Failed to create database tables: {e}")


def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    """Serve frontend files"""
    if path == '' or path == 'index.html':
        frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')
        return send_from_directory(frontend_dir, 'index.html')
    else:
        frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')
        return send_from_directory(frontend_dir, path)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect('/')

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect('/')
        flash('Invalid email or password', 'error')

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - Resume Analyzer</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
                color: #ffffff;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .login-container {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 2rem;
                width: 100%;
                max-width: 400px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            .login-header {
                text-align: center;
                margin-bottom: 2rem;
            }
            .login-header h1 {
                font-size: 2rem;
                margin-bottom: 0.5rem;
                background: linear-gradient(135deg, #00ff88, #00d4ff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .form-group {
                margin-bottom: 1.5rem;
            }
            .form-group label {
                display: block;
                margin-bottom: 0.5rem;
                color: rgba(255, 255, 255, 0.8);
            }
            .form-group input {
                width: 100%;
                padding: 0.75rem;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.05);
                color: #ffffff;
                font-size: 1rem;
            }
            .form-group input:focus {
                outline: none;
                border-color: #00d4ff;
                box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.2);
            }
            .btn {
                width: 100%;
                padding: 0.75rem;
                border: none;
                border-radius: 8px;
                background: linear-gradient(135deg, #00d4ff, #0099ff);
                color: #ffffff;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
            }
            .links {
                text-align: center;
                margin-top: 1.5rem;
            }
            .links a {
                color: #00d4ff;
                text-decoration: none;
                margin: 0 0.5rem;
            }
            .links a:hover {
                text-decoration: underline;
            }
            .flash-message {
                padding: 0.75rem;
                border-radius: 8px;
                margin-bottom: 1rem;
                text-align: center;
            }
            .flash-error {
                background: rgba(255, 107, 157, 0.2);
                border: 1px solid rgba(255, 107, 157, 0.3);
                color: #ff6b9d;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-header">
                <h1>Resume Analyzer</h1>
                <p>Sign in to your account</p>
            </div>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="flash-message flash-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <form method="POST">
                {{ form.hidden_tag() }}
                <div class="form-group">
                    {{ form.email.label }}
                    {{ form.email(class="form-control") }}
                    {% if form.email.errors %}
                        {% for error in form.email.errors %}
                            <small style="color: #ff6b9d;">{{ error }}</small>
                        {% endfor %}
                    {% endif %}
                </div>
                <div class="form-group">
                    {{ form.password.label }}
                    {{ form.password(class="form-control", type="password") }}
                    {% if form.password.errors %}
                        {% for error in form.password.errors %}
                            <small style="color: #ff6b9d;">{{ error }}</small>
                        {% endfor %}
                    {% endif %}
                </div>
                <div class="form-group">
                    {{ form.remember() }} {{ form.remember.label }}
                </div>
                <button type="submit" class="btn">Sign In</button>
            </form>

            <div class="links">
                <a href="{{ url_for('register') }}">Create Account</a>
            </div>
        </div>
    </body>
    </html>
    """, form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if current_user.is_authenticated:
        return redirect('/')

    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter(
            (User.email == form.email.data) | (User.username == form.username.data)
        ).first()

        if existing_user:
            if existing_user.email == form.email.data:
                flash('Email already registered', 'error')
            else:
                flash('Username already taken', 'error')
            return redirect(url_for('register'))

        # Create new user
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Register - Resume Analyzer</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
                color: #ffffff;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .register-container {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 2rem;
                width: 100%;
                max-width: 400px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            .register-header {
                text-align: center;
                margin-bottom: 2rem;
            }
            .register-header h1 {
                font-size: 2rem;
                margin-bottom: 0.5rem;
                background: linear-gradient(135deg, #00ff88, #00d4ff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .form-group {
                margin-bottom: 1.5rem;
            }
            .form-group label {
                display: block;
                margin-bottom: 0.5rem;
                color: rgba(255, 255, 255, 0.8);
            }
            .form-group input {
                width: 100%;
                padding: 0.75rem;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.05);
                color: #ffffff;
                font-size: 1rem;
            }
            .form-group input:focus {
                outline: none;
                border-color: #00d4ff;
                box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.2);
            }
            .btn {
                width: 100%;
                padding: 0.75rem;
                border: none;
                border-radius: 8px;
                background: linear-gradient(135deg, #00d4ff, #0099ff);
                color: #ffffff;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
            }
            .links {
                text-align: center;
                margin-top: 1.5rem;
            }
            .links a {
                color: #00d4ff;
                text-decoration: none;
                margin: 0 0.5rem;
            }
            .links a:hover {
                text-decoration: underline;
            }
            .flash-message {
                padding: 0.75rem;
                border-radius: 8px;
                margin-bottom: 1rem;
                text-align: center;
            }
            .flash-error {
                background: rgba(255, 107, 157, 0.2);
                border: 1px solid rgba(255, 107, 157, 0.3);
                color: #ff6b9d;
            }
            .flash-success {
                background: rgba(0, 255, 136, 0.2);
                border: 1px solid rgba(0, 255, 136, 0.3);
                color: #00ff88;
            }
        </style>
    </head>
    <body>
        <div class="register-container">
            <div class="register-header">
                <h1>Create Account</h1>
                <p>Join Resume Analyzer</p>
            </div>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="flash-message flash-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <form method="POST">
                {{ form.hidden_tag() }}
                <div class="form-group">
                    {{ form.username.label }}
                    {{ form.username(class="form-control") }}
                    {% if form.username.errors %}
                        {% for error in form.username.errors %}
                            <small style="color: #ff6b9d;">{{ error }}</small>
                        {% endfor %}
                    {% endif %}
                </div>
                <div class="form-group">
                    {{ form.email.label }}
                    {{ form.email(class="form-control") }}
                    {% if form.email.errors %}
                        {% for error in form.email.errors %}
                            <small style="color: #ff6b9d;">{{ error }}</small>
                        {% endfor %}
                    {% endif %}
                </div>
                <div class="form-group">
                    {{ form.password.label }}
                    {{ form.password(class="form-control", type="password") }}
                    {% if form.password.errors %}
                        {% for error in form.password.errors %}
                            <small style="color: #ff6b9d;">{{ error }}</small>
                        {% endfor %}
                    {% endif %}
                </div>
                <div class="form-group">
                    {{ form.confirm_password.label }}
                    {{ form.confirm_password(class="form-control", type="password") }}
                    {% if form.confirm_password.errors %}
                        {% for error in form.confirm_password.errors %}
                            <small style="color: #ff6b9d;">{{ error }}</small>
                        {% endfor %}
                    {% endif %}
                </div>
                <button type="submit" class="btn">Create Account</button>
            </form>

            <div class="links">
                <a href="{{ url_for('login') }}">Already have an account?</a>
            </div>
        </div>
    </body>
    </html>
    """, form=form)


@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    return redirect(url_for('login'))


@app.route('/app')
@login_required
def serve_frontend():
    """Serve the main frontend application"""
    return redirect('/')


@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    """
    Endpoint to analyze resume
    Expects: PDF file in 'file' form field
    Returns: JSON with analysis results
    """
    try:
        print(f"[DEBUG] /analyze request received from {request.remote_addr}")
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in request'}), 400
        
        file = request.files['file']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({'error': 'No file selected for uploading'}), 400
        
        # Check if file type is allowed
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        print(f"[DEBUG] Uploaded file saved to {filepath}")

        # Get file size
        file_size = os.path.getsize(filepath)

        # Analyze the resume
        analysis_result = analyze_resume(filepath)
        print(f"[DEBUG] Analysis result produced for {filename}")

        # Save to database with user association
        try:
            resume = Resume(
                filename=filename,
                original_filename=file.filename,
                file_size=file_size,
                raw_text=analysis_result.get('raw_text'),
                word_count=analysis_result.get('word_count'),
                page_count=analysis_result.get('page_count'),
                contact_info=analysis_result.get('contact_info'),
                skills=analysis_result.get('skills'),
                experience_count=analysis_result.get('experience_count'),
                education_found=analysis_result.get('education_found'),
                score=analysis_result.get('score'),
                suggestions=analysis_result.get('suggestions'),
                user_id=current_user.id
            )
            db.session.add(resume)
            db.session.commit()
            print(f"[DEBUG] Resume saved to database with ID: {resume.id} for user {current_user.username}")

            # Add database ID to response
            analysis_result['id'] = resume.id

        except Exception as db_error:
            print(f"[ERROR] Failed to save to database: {db_error}")
            db.session.rollback()
            # Continue with response even if database save fails

        # Clean up: remove uploaded file
        try:
            os.remove(filepath)
        except Exception as cleanup_err:
            print(f"[WARNING] Failed to remove uploaded file: {cleanup_err}")

        return jsonify({
            'success': True,
            'data': analysis_result
        }), 200
    
    except Exception as e:
        # Log error for debugging
        print(f"Error in /analyze: {str(e)}")
        print(traceback.format_exc())
        
        return jsonify({
            'error': 'An error occurred while analyzing the resume',
            'details': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


@app.route('/auth/status', methods=['GET'])
def auth_status():
    """Check authentication status"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email
            }
        }), 200
    else:
        return jsonify({'authenticated': False}), 401


@app.route('/resumes', methods=['GET'])
@login_required
def get_resumes():
    """Get all stored resumes for the current user"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.upload_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'success': True,
            'data': [resume.to_dict() for resume in resumes.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': resumes.total,
                'pages': resumes.pages,
                'has_next': resumes.has_next,
                'has_prev': resumes.has_prev
            }
        }), 200

    except Exception as e:
        print(f"Error in /resumes: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve resumes',
            'details': str(e)
        }), 500


@app.route('/resumes/<int:resume_id>', methods=['GET'])
@login_required
def get_resume(resume_id):
    """Get a specific resume by ID for the current user"""
    try:
        resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
        return jsonify({
            'success': True,
            'data': resume.to_dict()
        }), 200

    except Exception as e:
        print(f"Error in /resumes/{resume_id}: {str(e)}")
        return jsonify({
            'error': 'Resume not found',
            'details': str(e)
        }), 404


@app.route('/resumes/<int:resume_id>', methods=['DELETE'])
@login_required
def delete_resume(resume_id):
    """Delete a specific resume for the current user"""
    try:
        resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
        db.session.delete(resume)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Resume {resume_id} deleted successfully'
        }), 200

    except Exception as e:
        print(f"Error deleting resume {resume_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'error': 'Failed to delete resume',
            'details': str(e)
        }), 500


@app.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """Get resume analysis statistics for the current user"""
    try:
        total_resumes = Resume.query.filter_by(user_id=current_user.id).count()
        avg_score = db.session.query(db.func.avg(Resume.score)).filter(Resume.user_id == current_user.id).scalar() or 0
        avg_score = round(float(avg_score), 2)

        # Skills frequency
        all_skills = []
        resumes = Resume.query.filter_by(user_id=current_user.id).all()
        for resume in resumes:
            if resume.skills:
                all_skills.extend(resume.skills)

        skill_counts = {}
        for skill in all_skills:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1

        return jsonify({
            'success': True,
            'data': {
                'total_resumes': total_resumes,
                'average_score': avg_score,
                'skill_counts': skill_counts
            }
        }), 200

    except Exception as e:
        print(f"Error in /stats: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve stats',
            'details': str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)