from dataclasses import dataclass

from llm_client import LLM_client
from scrapers.indeed import IndeedScraper
from job import JobScore, Job


@dataclass
class Profile:
    cv_file_path: str
    location: str

def user_profile_to_rated_jobs(profile: Profile) -> list[JobScore]:
    # 1: Load CV file as a gemini file
    client = LLM_client(file_path=profile.cv_file_path)
    print("Loaded CV file to memory.\n")
    
    # 2: Generate job titles matching CV
    print("Generating job titles for CV...")
    job_titles = client.cv_to_job_titles()
    print("Generated job titles: " + str(job_titles) + "\n")
    
    # 3: Scrape jobs for each title
    jobs: list[Job] = []
    scraper = IndeedScraper()
    
    for title in job_titles:
        print(f"Scraping Indeed for {title} roles...")
        job_results = scraper.get_jobs(query=title, location=profile.location)
        print(f"Found {str(len(job_results))} jobs\n")
        jobs.extend(job_results)
    
    # 4: Score each job
    job_scores: list[JobScore] = []
    
    for i,job in enumerate(jobs):
        print(f"Scoring job {str(i)}/{str(len(jobs))}")
        score = client.analyze_job(job=job)
        
        job_scores.append(score)
    
    return job_scores


if __name__ == "__main__":
    file_path = "temps/cv.pdf"
    location = "Tel Aviv-Jaffa, מחוז תל אביב"
    
    profile = Profile(file_path, location)
    
    scores = user_profile_to_rated_jobs(profile)
    
    print(scores)