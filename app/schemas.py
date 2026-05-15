from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID
from typing import Optional

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    location: Optional[str] = None
    titles: Optional[list[str]] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    location: Optional[str] = None
    titles: Optional[list[str]] = None

class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    location: Optional[str] = None
    titles: Optional[list[str]] = None
    cv_filename: Optional[str] = None
    cv_path: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobScoreResponse(BaseModel):
    job_id: UUID
    title: str
    company_name: Optional[str] = None
    company_link: Optional[str] = None
    location: str
    description: str
    job_link: str
    cv_fit: int
    job_quality: int
    overall: int
    summary: str
    liked: Optional[bool] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnratedJobsResponse(BaseModel):
    total_unrated: int
    jobs: list[JobScoreResponse]
