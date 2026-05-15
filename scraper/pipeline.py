import sys
import os
import time
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from .llm_client import LLM_client
from .job import JobScore, Job, JobScraper
from .scrapers.indeed import IndeedScraper
from app.models import User
from app.database import SessionLocal
from app.crud import add_title as add_title_to_db
from app.crud import get_user_titles, save_job_and_score, clear_titles

# Get project root directory (parent of scraper directory)
PROJECT_ROOT = str(Path(__file__).parent.parent.resolve())
UPLOAD_DIR = os.path.join(PROJECT_ROOT, os.getenv("UPLOAD_DIR", "uploads").lstrip("./"))


def generate_titles_and_save(user: User) -> list[str]:
    """Generate job titles from user's CV and save them to database"""
    db = SessionLocal()
    try:
        # Check if user has a CV
        if not user.cv_path:
            print(f"No CV found for user {user.id}")
            return []

        # Construct full path to CV file
        cv_file_path = os.path.join(UPLOAD_DIR, user.cv_path)
        print(f"Generating titles for user {user.id}...")
        client = LLM_client(file_path=cv_file_path)
        job_titles = client.cv_to_job_titles()

        print(f"Generated titles: {job_titles}")

        clear_titles(db, user.id)

        for title in job_titles:
            add_title_to_db(db, user.id, title)

        print(f"Saved {len(job_titles)} titles to database")
        
        return job_titles
    except Exception as e:
        print(f"Error generating titles: {str(e)}")
        return []
    finally:
        db.close()


def analyze_jobs_and_save(user: User) -> list[JobScore]:
    """Analyze jobs from user's titles and save scores to database"""
    db = SessionLocal()
    try:
        # Check if user has a CV
        if not user.cv_path:
            print(f"No CV found for user {user.id}")
            return []

        # Load titles with retry (race condition with generate_titles_and_save)
        titles = get_user_titles(db, user.id)
        max_retries = 3
        for attempt in range(max_retries):
            if titles:
                break
            if attempt < max_retries - 1:
                print(f"Waiting for titles to be saved (attempt {attempt + 1}/{max_retries})...")
                time.sleep(2)
                titles = get_user_titles(db, user.id)

        if not titles:
            print(f"No titles found for user {user.id} after retries, skipping job analysis")
            return []

        print(f"Analyzing jobs for user {user.id} with titles: {titles}")

        # Init
        jobs: list[Job] = []
        # Construct full path to CV file
        cv_file_path = os.path.join(UPLOAD_DIR, user.cv_path)
        client = LLM_client(file_path=cv_file_path)
        scraper = IndeedScraper()

        # Scrape jobs for each title
        for title in titles[:1]:
            try:
                print(f"Scraping jobs for title: {title}")
                job_results = scraper.get_jobs(
                    query=title,
                    location=user.location,
                    num_jobs=1
                )
                jobs.extend(job_results)
                print(f"Found {len(job_results)} jobs for {title}")
            except Exception as e:
                print(f"Error scraping jobs for {title}: {str(e)}")
                continue

        if not jobs:
            print(f"No jobs found for user {user.id}")
            return []

        # Score each job
        job_scores: list[JobScore] = []
        for i, job in enumerate(jobs):
            try:
                print(f"Scoring job {i+1}/{len(jobs)}: {job.title}")
                score = client.analyze_job(job)
                job_scores.append(score)
            except Exception as e:
                print(f"Error scoring job: {str(e)}")
                continue

        # Save to DB
        print(f"Saving {len(job_scores)} job scores to database")
        for job_score in job_scores:
            try:
                save_job_and_score(db, user.id, job_score)
            except Exception as e:
                print(f"Error saving job score: {str(e)}")
                continue

        print(f"Completed job analysis for user {user.id}")
        return job_scores

    except Exception as e:
        print(f"Error in analyze_jobs_and_save: {str(e)}")
        return []
    finally:
        db.close()


def run_pipeline(user: User):
    titles = generate_titles_and_save(user)
    jobs_scores = analyze_jobs_and_save(user)