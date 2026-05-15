"""LLM Client using LangChain with Google Generative AI"""
import os
import json
import sys
from pathlib import Path
from google import genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from secrets_manager import get_gemini_api_key
from .job import Job, JobScore
from .prompts import CV_TO_JOBS_PROMPT, JOB_SCORE_PROMPT

# Singleton model instance (reuse the LLM model across clients)
_model: ChatGoogleGenerativeAI = None

def _get_model() -> ChatGoogleGenerativeAI:
    """Get or create the LLM model singleton"""
    global _model
    if _model is None:
        _model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            api_key=get_gemini_api_key(),
            temperature=0,
            top_p=0.95
        )
    return _model


class LLMClient:
    """LLM Client for CV analysis and job scoring using LangChain"""

    def __init__(self, file_path: str):
        """Initialize client with CV file"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File doesn't exist. path: {file_path}")

        self.cv_file_path = file_path
        self.model = _get_model()  # Reuse singleton model

        # Upload file to Google API for multimodal support
        self.genai_client = genai.Client(api_key=get_gemini_api_key())
        try:
            self.cv_file = self.genai_client.files.upload(file=file_path)
            print(f"CV file uploaded: {self.cv_file.name}")
        except Exception as e:
            print(f"Warning: Failed to upload file to Google API: {e}")
            # Fallback: read file content directly
            self.cv_file = None
            self.cv_content = self._read_cv_file(file_path)

    @staticmethod
    def _read_cv_file(file_path: str) -> str:
        """Read CV file content"""
        try:
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            return "\n".join([doc.page_content for doc in documents])
        except Exception as e:
            print(f"Warning: Could not parse PDF: {e}. Using file path as fallback.")
            return f"CV File: {file_path}"

    def cv_to_job_titles(self) -> list[str]:
        """Extract job titles from CV using LLM"""
        messages = [
            SystemMessage(content="You are a professional recruiter analyzing CVs."),
            HumanMessage(content=f"""
Based on this CV content, extract 5 relevant job titles that would be a good match.
Return ONLY a JSON object with a "titles" array, nothing else.

CV Content:
{self.cv_content}

{CV_TO_JOBS_PROMPT}
""")
        ]

        # Retry logic
        for attempt in range(3):
            try:
                response = self.model.invoke(messages)
                response_text = response.content

                # Handle markdown formatting
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]

                data = json.loads(response_text.strip())
                return data.get("titles", [])
            except json.JSONDecodeError:
                if attempt < 2:
                    continue
                raise ValueError(f"Failed to parse LLM response as JSON: {response.content}")

    def analyze_job(self, job: Job) -> JobScore:
        """Analyze a job posting against the CV"""
        messages = [
            SystemMessage(content="You are a professional recruiter evaluating job matches."),
            HumanMessage(content=f"""
Based on the CV content provided, analyze this job posting and provide scores.
Return ONLY a JSON object with cv_fit, job_quality, overall (1-100), and summary.

CV Content:
{self.cv_content}

Job Details:
Title: {job.title}
Company: {job.company_name}
Location: {job.location}
Description: {job.description}

{JOB_SCORE_PROMPT}
""")
        ]

        response = self.model.invoke(messages)
        response_text = response.content

        # Handle markdown formatting
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        data = json.loads(response_text.strip())

        return JobScore(
            job=job,
            cv_fit=int(data["cv_fit"]),
            job_quality=int(data["job_quality"]),
            overall=int(data["overall"]),
            summary=data["summary"]
        )
