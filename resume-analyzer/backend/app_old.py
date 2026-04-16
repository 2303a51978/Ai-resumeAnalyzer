from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import traceback
from werkzeug.utils import secure_filename
from analyzer import analyze_resume
from models import db, Resume
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///resumes.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Initialize database
db.init_app(app)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 10 * 1024 * 1024))  # 10MB default

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


def create_tables():
    """Create database tables"""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")


# Create tables on first run
with app.app_context():
    try:
        db.create_all()
        print("[INFO] Database tables verified/created")
    except Exception as e:
        print(f"[ERROR] Failed to create database tables: {e}")


def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/analyze', methods=['POST'])
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

        # Save to database
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
                suggestions=analysis_result.get('suggestions')
            )
            db.session.add(resume)
            db.session.commit()
            print(f"[DEBUG] Resume saved to database with ID: {resume.id}")

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


@app.route('/resumes', methods=['GET'])
def get_resumes():
    """Get all stored resumes"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        resumes = Resume.query.order_by(Resume.upload_date.desc()).paginate(
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
def get_resume(resume_id):
    """Get a specific resume by ID"""
    try:
        resume = Resume.query.get_or_404(resume_id)
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
def delete_resume(resume_id):
    """Delete a specific resume"""
    try:
        resume = Resume.query.get_or_404(resume_id)
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
def get_stats():
    """Get resume analysis statistics"""
    try:
        total_resumes = Resume.query.count()
        avg_score = db.session.query(db.func.avg(Resume.score)).scalar() or 0
        avg_score = round(float(avg_score), 2)

        # Skills frequency
        all_skills = []
        resumes = Resume.query.all()
        for resume in resumes:
            if resume.skills:
                all_skills.extend(resume.skills)

        skill_counts = {}
        for skill in all_skills:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1

        top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return jsonify({
            'success': True,
            'data': {
                'total_resumes': total_resumes,
                'average_score': avg_score,
                'top_skills': top_skills
            }
        }), 200

    except Exception as e:
        print(f"Error in /stats: {str(e)}")
        return jsonify({
            'error': 'Failed to get statistics',
            'details': str(e)
        }), 500


@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({'error': 'File is too large. Maximum size is 10MB'}), 413


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
