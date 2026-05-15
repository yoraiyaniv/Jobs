"""Database operations for Job and JobScore"""
import sys
from pathlib import Path
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.job import Job as JobDataclass, JobScore as JobScoreDataclass
from .models import Job, JobScore, User


def create_job(
    db: Session,
    user_id: UUID,
    job_data: JobDataclass
) -> Job:
    """Create a new job record"""
    db_job = Job(
        user_id=user_id,
        title=job_data.title,
        location=job_data.location,
        description=job_data.description,
        job_link=job_data.job_link,
        company_name=job_data.company_name,
        company_link=job_data.company_link
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


def create_job_score(
    db: Session,
    user_id: UUID,
    job_id: UUID,
    score_data: JobScoreDataclass
) -> JobScore:
    """Create a new job score record"""
    db_score = JobScore(
        user_id=user_id,
        job_id=job_id,
        cv_fit=score_data.cv_fit,
        job_quality=score_data.job_quality,
        overall=score_data.overall,
        summary=score_data.summary
    )
    db.add(db_score)
    db.commit()
    db.refresh(db_score)
    return db_score


def save_job_and_score(
    db: Session,
    user_id: UUID,
    job_score_data: JobScoreDataclass
) -> tuple[Job, JobScore]:
    """Save both job and score in one operation"""
    # Create job
    db_job = create_job(db, user_id, job_score_data.job)

    # Create score
    db_score = create_job_score(db, user_id, db_job.id, job_score_data)

    return db_job, db_score


def get_user_jobs(
    db: Session,
    user_id: UUID,
    limit: int = 100,
    offset: int = 0
) -> list[Job]:
    """Get all jobs for a user"""
    return db.query(Job).filter(Job.user_id == user_id).limit(limit).offset(offset).all()


def get_user_job_scores(
    db: Session,
    user_id: UUID,
    limit: int = 100,
    offset: int = 0
) -> list[JobScore]:
    """Get all job scores for a user"""
    return db.query(JobScore).filter(JobScore.user_id == user_id).limit(limit).offset(offset).all()


def get_jobs_with_scores(
    db: Session,
    user_id: UUID,
    limit: int = 100,
    offset: int = 0
) -> list[tuple[Job, JobScore]]:
    """Get all jobs with their scores for a user, ordered by overall score"""
    results = (
        db.query(Job, JobScore)
        .filter(Job.user_id == user_id)
        .filter(JobScore.job_id == Job.id)
        .order_by(JobScore.overall.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return results


def get_unrated_jobs_with_scores(
    db: Session,
    user_id: UUID,
    limit: int = 100,
    offset: int = 0
) -> list[tuple[Job, JobScore]]:
    """Get jobs that haven't been rated (liked is None), ordered by overall score"""
    results = (
        db.query(Job, JobScore)
        .filter(Job.user_id == user_id)
        .filter(Job.liked == None)  # Not rated
        .filter(JobScore.job_id == Job.id)
        .order_by(JobScore.overall.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return results


def update_job_liked_status(
    db: Session,
    job_id: UUID,
    liked: bool | None
) -> Job:
    """Update the liked/disliked status of a job"""
    db_job = db.query(Job).filter(Job.id == job_id).first()
    if db_job:
        db_job.liked = liked
        db.commit()
        db.refresh(db_job)
    return db_job


def get_liked_jobs(
    db: Session,
    user_id: UUID
) -> list[Job]:
    """Get all liked jobs for a user"""
    return db.query(Job).filter(
        Job.user_id == user_id,
        Job.liked == True
    ).all()


def get_disliked_jobs(
    db: Session,
    user_id: UUID
) -> list[Job]:
    """Get all disliked jobs for a user"""
    return db.query(Job).filter(
        Job.user_id == user_id,
        Job.liked == False
    ).all()


def delete_job(
    db: Session,
    job_id: UUID
) -> bool:
    """Delete a job and its associated scores"""
    # Delete scores first
    db.query(JobScore).filter(JobScore.job_id == job_id).delete()

    # Delete job
    result = db.query(Job).filter(Job.id == job_id).delete()
    db.commit()

    return result > 0


# ============= TITLES OPERATIONS =============

def add_title(
    db: Session,
    user_id: UUID,
    title: str
) -> User:
    """Add a title to a user's titles list"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    if user.titles is None:
        user.titles = []

    if title not in user.titles:
        user.titles.append(title)
        flag_modified(user, "titles")  # Tell SQLAlchemy the column was modified
        db.commit()
        db.refresh(user)

    return user


def remove_title(
    db: Session,
    user_id: UUID,
    title: str
) -> User:
    """Remove a title from a user's titles list"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    if user.titles and title in user.titles:
        user.titles.remove(title)
        db.commit()
        db.refresh(user)

    return user


def set_titles(
    db: Session,
    user_id: UUID,
    titles: list[str]
) -> User:
    """Replace all titles for a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    user.titles = titles if titles else None
    flag_modified(user, "titles")  # Tell SQLAlchemy the column was modified
    db.commit()
    db.refresh(user)
    return user


def get_user_titles(
    db: Session,
    user_id: UUID
) -> list[str]:
    """Get all titles for a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.titles:
        return []
    return user.titles


def clear_titles(
    db: Session,
    user_id: UUID
) -> User:
    """Clear all titles for a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    user.titles = None
    flag_modified(user, "titles")  # Tell SQLAlchemy the column was modified
    db.commit()
    db.refresh(user)
    return user
