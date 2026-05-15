from google import genai
from google.genai import types
import os
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from secrets_manager import get_gemini_api_key
from .job import Job, JobScore
from .prompts import CV_TO_JOBS_PROMPT, JOB_SCORE_PROMPT


class LLM_client:
    def __init__(self, file_path: str):
        self.client = genai.Client(api_key=get_gemini_api_key())
        self.model = "gemini-2.5-flash-lite"
        
        if os.path.exists(file_path):
            file = self.client.files.upload(file=file_path)
            self.cv_file = file
        else:
            raise FileNotFoundError(f"File doesn't exist. path: {file_path}")    
        
    def cv_to_job_titles(self) -> list[str]: 
        request_contents = [
            types.Part.from_uri(file_uri=self.cv_file.uri, mime_type="application/pdf"),
            CV_TO_JOBS_PROMPT
        ]
        
        for i in range(3):
            response = self.client.models.generate_content(
                model = self.model,
                contents=request_contents,
                config=types.GenerateContentConfig(response_mime_type="application/json")
                )
            if response.text:
                break
        
        titles = json.loads(response.text)["titles"]
        
        return titles
    
    def analyze_job(self, job: Job) -> JobScore:
        request_contents = [
            types.Part.from_uri(file_uri=self.cv_file.uri, mime_type="application/pdf"),
            JOB_SCORE_PROMPT.format(
                title=job.title,
                company_name=job.company_name,
                location=job.location,
                description=job.description
            )
        ]
        
        response = self.client.models.generate_content(
            model = self.model,
            contents=request_contents,
            config=types.GenerateContentConfig(response_mime_type="application/json")
            )

        data = json.loads(response.text)

        return JobScore(
            job=job,
            cv_fit=data["cv_fit"],
            job_quality=data["job_quality"],
            overall=data["overall"],
            summary=data["summary"]
        )