import PyPDF2
import re
from datetime import datetime


def analyze_resume(filepath):
    """
    Analyze a resume PDF and extract key information
    
    Args:
        filepath: Path to the PDF file
    
    Returns:
        Dictionary with extracted resume data
    """
    try:
        # Extract text from PDF
        text = extract_text_from_pdf(filepath)
        
        # Parse resume content
        analysis = {
            'raw_text': text[:500],  # First 500 chars
            'word_count': len(text.split()),
            'page_count': count_pdf_pages(filepath),
            'contact_info': extract_contact_info(text),
            'skills': extract_skills(text),
            'experience_count': count_experience_keywords(text),
            'education_found': bool(extract_education_keywords(text)),
            'score': calculate_resume_score(text),
            'suggestions': get_suggestions(text)
        }
        
        return analysis
    
    except Exception as e:
        raise Exception(f"Failed to analyze resume: {str(e)}")


def extract_text_from_pdf(filepath):
    """Extract text from PDF file"""
    text = ""
    try:
        with open(filepath, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            print(f"[DEBUG] PDF loaded with {len(pdf_reader.pages)} pages")
            for index, page in enumerate(pdf_reader.pages, start=1):
                page_text = page.extract_text()
                print(f"[DEBUG] Page {index} extracted text length: {len(page_text or '')}")
                if page_text:
                    text += page_text
        return text
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")


def count_pdf_pages(filepath):
    """Count number of pages in PDF"""
    try:
        with open(filepath, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return len(pdf_reader.pages)
    except Exception as e:
        return 0


def extract_contact_info(text):
    """Extract contact information (email, phone)"""
    contact = {}
    
    # Email pattern
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    if emails:
        contact['email'] = emails[0]
    
    # Phone pattern (basic)
    phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    phones = re.findall(phone_pattern, text)
    if phones:
        contact['phone'] = phones[0]
    
    # LinkedIn pattern
    linkedin_pattern = r'linkedin\.com/in/[\w-]+'
    linkedin = re.findall(linkedin_pattern, text, re.IGNORECASE)
    if linkedin:
        contact['linkedin'] = linkedin[0]
    
    return contact


def extract_skills(text):
    """Extract potential skills from resume"""
    common_skills = [
        'python', 'java', 'javascript', 'c#', 'c++', 'typescript',
        'react', 'angular', 'vue', 'node.js', 'django', 'flask',
        'sql', 'mongodb', 'postgresql', 'mysql',
        'html', 'css', 'git', 'linux', 'aws', 'azure',
        'docker', 'kubernetes', 'machine learning', 'data analysis',
        'project management', 'agile', 'scrum', 'leadership'
    ]
    
    text_lower = text.lower()
    found_skills = [skill for skill in common_skills if skill in text_lower]
    
    return found_skills


def count_experience_keywords(text):
    """Count keywords indicating professional experience"""
    experience_keywords = ['experience', 'worked', 'developed', 'managed', 'led', 'responsible']
    text_lower = text.lower()
    count = sum(text_lower.count(keyword) for keyword in experience_keywords)
    return count


def extract_education_keywords(text):
    """Check for education-related keywords"""
    education_keywords = ['bachelor', 'master', 'phd', 'degree', 'university', 'college', 'diploma']
    text_lower = text.lower()
    found = [kw for kw in education_keywords if kw in text_lower]
    return found


def calculate_resume_score(text):
    """Calculate a basic resume quality score (0-100)"""
    score = 50  # Base score
    
    # Check for contact info
    if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text):
        score += 10
    
    # Check for experience keywords
    if sum(text.lower().count(kw) for kw in ['experience', 'worked', 'developed']) > 5:
        score += 15
    
    # Check for education
    if any(kw in text.lower() for kw in ['bachelor', 'master', 'university']):
        score += 10
    
    # Check for skills
    common_skills = ['python', 'java', 'javascript', 'react', 'aws']
    if sum(text.lower().count(skill) for skill in common_skills) > 0:
        score += 15
    
    return min(score, 100)  # Cap at 100


def get_suggestions(text):
    """Generate suggestions for resume improvement"""
    suggestions = []
    
    if not re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text):
        suggestions.append('Add email address to resume')
    
    if not re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text):
        suggestions.append('Add phone number to resume')
    
    if text.count('\n') < 10:
        suggestions.append('Add more sections or details to your resume')
    
    if len(text.split()) < 100:
        suggestions.append('Resume appears short, consider adding more details')
    
    if not any(kw in text.lower() for kw in ['bachelor', 'master', 'university']):
        suggestions.append('Include your educational background')
    
    return suggestions
