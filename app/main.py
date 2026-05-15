import os
import sys
import uuid
from pathlib import Path
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from .database import get_db, engine
from .models import Base, User
from .schemas import UserResponse
from scraper.pipeline import run_pipeline as find_jobs
from scraper.pipeline import analyze_jobs_and_save

load_dotenv()

app = FastAPI()

@app.on_event("startup")
def startup():
    """Create tables on startup"""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Could not create tables on startup: {e}")

# Setup Jinja2
templates = Environment(loader=FileSystemLoader("templates"))

# Setup static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Ensure upload directory exists
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
CV_DIR = UPLOAD_DIR / "cvs"
CV_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serve the dashboard HTML"""
    template = templates.get_template("index.html")
    return template.render()


@app.get("/jobs", response_class=HTMLResponse)
def get_jobs_page():
    """Serve the job rating page"""
    template = templates.get_template("jobs.html")
    return template.render()


@app.get("/api/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    """Get all users"""
    users = db.query(User).all()
    return users


@app.post("/api/users", response_model=UserResponse)
def create_user(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    email: str = Form(...),
    location: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Create a new user"""
    try:
        db_user = User(
            name=name,
            email=email,
            location=location
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return db_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")


@app.get("/api/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    """Get a single user"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/api/users/{user_id}/unrated-jobs")
def get_unrated_jobs(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get unrated jobs for a user with their scores"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    # Verify user exists
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Import here to avoid circular imports
    from .crud import get_unrated_jobs_with_scores

    # Get unrated jobs with scores
    jobs_with_scores = get_unrated_jobs_with_scores(
        db, user_uuid, limit=limit, offset=offset
    )

    # Format response
    jobs = []
    for job, score in jobs_with_scores:
        jobs.append({
            "job_id": str(job.id),
            "title": job.title,
            "company_name": job.company_name,
            "company_link": job.company_link,
            "location": job.location,
            "description": job.description,
            "job_link": job.job_link,
            "cv_fit": score.cv_fit,
            "job_quality": score.job_quality,
            "overall": score.overall,
            "summary": score.summary,
            "liked": job.liked,
            "created_at": score.created_at
        })

    return {
        "total_unrated": len(jobs),
        "jobs": jobs
    }


@app.put("/api/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Update a user"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    db_user = db.query(User).filter(User.id == user_uuid).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        if name is not None:
            db_user.name = name
        if email is not None:
            db_user.email = email
        if location is not None:
            db_user.location = location

        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")


@app.delete("/api/users/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    """Delete a user"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    db_user = db.query(User).filter(User.id == user_uuid).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete CV file if it exists
    if db_user.cv_path:
        cv_path = CV_DIR / db_user.cv_path.split("/")[-1]
        if cv_path.exists():
            cv_path.unlink()

    db.delete(db_user)
    db.commit()
    return {"message": "User deleted"}


@app.post("/api/users/{user_id}/cv")
def upload_cv(user_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a CV for a user"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    db_user = db.query(User).filter(User.id == user_uuid).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate file type
    allowed_extensions = {".pdf", ".doc", ".docx"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="File must be PDF or DOC")

    try:
        # Generate unique filename
        unique_filename = f"{user_uuid}_{file.filename}"
        cv_path = CV_DIR / unique_filename

        # Save file
        with open(cv_path, "wb") as f:
            f.write(file.file.read())

        # Update user
        db_user.cv_filename = file.filename
        db_user.cv_path = f"cvs/{unique_filename}"
        db.commit()
        db.refresh(db_user)

        background_tasks.add_task(find_jobs, db_user)
        
        return db_user
    except Exception as e:
        db.rollback()
        print(f"CV upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@app.post("/api/jobs/{job_id}/rate")
def rate_job(
    job_id: str,
    body: dict,
    db: Session = Depends(get_db)
):
    """Rate a job as liked or disliked"""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID")

    liked = body.get("liked")
    if liked is None:
        raise HTTPException(status_code=400, detail="Missing 'liked' field")

    from .crud import update_job_liked_status

    job = update_job_liked_status(db, job_uuid, liked)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": str(job.id),
        "title": job.title,
        "liked": job.liked,
        "message": f"Job marked as {'liked' if liked else 'disliked'}"
    }


@app.post("/api/users/{user_id}/analyze-jobs")
def trigger_job_analysis(user_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger job analysis for a user using their existing titles"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.cv_path:
        raise HTTPException(status_code=400, detail="User has no CV uploaded")

    if not user.titles:
        raise HTTPException(status_code=400, detail="User has no job titles. Generate titles first.")

    background_tasks.add_task(analyze_jobs_and_save, user)
    return {"message": "Job analysis started in background"}


@app.get("/cv/{filename}")
def download_cv(filename: str):
    """Download a CV file"""
    # Security: only allow files in the CV directory
    try:
        # Decode and validate filename
        cv_path = CV_DIR / filename

        # Ensure the resolved path is within CV_DIR
        if not str(cv_path.resolve()).startswith(str(CV_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")

        if not cv_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(cv_path, media_type="application/octet-stream", filename=filename)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to download file")