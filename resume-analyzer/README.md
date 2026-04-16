# Resume Analyzer

AI-powered resume analysis tool with Flask backend, SQLite database, and modern frontend.

## Features

- **User Authentication** - Secure login and registration system
- PDF resume upload and analysis
- Resume scoring (0-100)
- Contact information extraction
- Skills detection
- Resume statistics
- Improvement suggestions
- **Database storage** - Store and retrieve analyzed resumes
- **Resume management** - View, delete stored resumes
- **Analytics** - Statistics on stored resumes
- Modern glassmorphism UI

## Authentication

The application now requires user authentication. Users must register and login to access the resume analysis features.

### User Registration
- Create an account with username, email, and password
- Passwords are securely hashed and stored

### User Login
- Login with email and password
- Session-based authentication
- Automatic logout on session expiry

## Database Setup

The application uses SQLite for simple, file-based storage. No additional database setup is required!

The database file (`resumes.db`) will be created automatically in the `backend/` directory when you first run the application.

For production use with multiple users, consider switching to PostgreSQL by:
1. Installing PostgreSQL
2. Updating `backend/.env` with PostgreSQL connection string
3. Adding `psycopg2-binary` to requirements.txt

## Quick Start

1. **Setup database** (see Database Setup section above)

2. **Install dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Run the application:**
   ```bash
   python run.py
   ```

4. **Open http://127.0.0.1:5000 in your browser**

5. **Register a new account or login if you already have one**

The `run.py` script will automatically:
- Install Python dependencies
- Setup database tables
- Start the Flask server with authentication

## Manual Start

### Backend
```bash
cd backend
python app.py
```

Then open http://127.0.0.1:5000

The Flask server now serves both the authentication pages and the frontend application.

## API Endpoints

**Note:** All endpoints except `/health`, `/login`, and `/register` require user authentication.

### Authentication Endpoints
- `GET /login` - Login page
- `POST /login` - Process login
- `GET /register` - Registration page  
- `POST /register` - Process registration
- `GET /logout` - Logout user

### Core Endpoints (Require Authentication)
- `GET /health` - Health check
- `POST /analyze` - Analyze resume PDF (stores results in database)

### Database Endpoints (Require Authentication)
- `GET /resumes` - Get all stored resumes (paginated)
- `GET /resumes/<id>` - Get specific resume by ID
- `DELETE /resumes/<id>` - Delete resume by ID
- `GET /stats` - Get resume analysis statistics

## Technologies

- Backend: Flask, SQLAlchemy, SQLite, PyPDF2
- Frontend: HTML5, CSS3, JavaScript (ES6+)
- UI: Glassmorphism design with CSS animations
- Database: SQLite with SQLAlchemy ORM (easily upgradeable to PostgreSQL)

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running
- Verify DATABASE_URL in `backend/.env`
- Check database credentials and permissions

### Frontend Connection Issues
- Ensure both servers are running
- Check browser console for errors
- Verify CORS settings
- Make sure frontend is served from HTTP server (not file://)

### Common Issues
- **"Table doesn't exist"**: Database tables are created automatically on first run
- **"Connection refused"**: Check if PostgreSQL service is running
- **"CORS error"**: Backend CORS is configured for cross-origin requests

## License

MIT