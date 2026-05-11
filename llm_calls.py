from google import genai
from google.genai import types
import os
import json

from secrets_manager import get_gemini_api_key


client = genai.Client(api_key=get_gemini_api_key())

CV_TO_JOBS_PROMPT = """Based on this CV, generate 5 strategic job search titles.
- Reflect the person's most recent and senior experience
- Be specific enough to be meaningful but broad enough to return job board results
- Combine role + domain where relevant (e.g. 'Backend Engineer', 'AI Platform Engineer')
- Avoid generic titles like 'Software Engineer' or 'Developer'
Return ONLY a JSON object like: {"titles": ["title1", "title2"]}"""

def cv_to_job_titles(file_path: str) -> list[str]: 
    if os.path.exists(file_path):
        file = client.files.upload(file=file_path)
    else:
        raise ValueError("File dose'nt exist.")
    
    request_contents = [
        types.Part.from_uri(file_uri=file.uri, mime_type="application/pdf"),
        CV_TO_JOBS_PROMPT
    ]
    
    response = client.models.generate_content(
        model = "gemini-2.5-flash",
        contents=request_contents,
        config=types.GenerateContentConfig(response_mime_type="application/json")
        )
    
    titles = json.loads(response.text)["titles"]
    
    return titles


if __name__ == "__main__":
    
    file_path = "temps/cv.pdf"
    titles = cv_to_job_titles(file_path=file_path)
    print(titles)