CV_TO_JOBS_PROMPT = """Based on this CV, generate 5 strategic job search titles.
- Reflect the person's most recent and senior experience
- Be specific enough to be meaningful but broad enough to return job board results
- Combine role + domain where relevant (e.g. 'Backend Engineer', 'AI Platform Engineer')
- Avoid generic titles like 'Software Engineer' or 'Developer'
Return ONLY a JSON object like: {"titles": ["title1", "title2"]}"""

JOB_SCORE_PROMPT = """You are a senior recruiter evaluating a job listing against a candidate's CV.
Job:
Title: {title}
Company: {company_name}
Location: {location}
Description: {description}

Consider the following when forming your scores:
- Skills and tech stack overlap
- Seniority and years of experience alignment
- Industry and domain relevance
- Role scope and growth potential
- Listing quality (clarity, specificity, red flags, compensation transparency)
- Company signals (stage, brand, culture hints)

Distill everything into three whole number percentages (0–100) and a concise summary.

Return ONLY a JSON object:
{{
  "cv_fit": <int>,
  "job_quality": <int>,
  "overall": <int>,
  "summary": "<2–3 sentences covering fit, opportunity quality, and any notable concerns>"
}}"""