from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class Job:
    title: str
    location: str
    description: str
    company_name: Optional[str]
    company_link: Optional[str]
    

class JobScraper(ABC):
    @abstractmethod
    def lookup(self, query: str, location: str) -> list[str]:
        """Lookup job listings site with the required filters and get the top job listing gathered as full links"""
        pass
    
    @abstractmethod
    def extract_job(self, url: str) -> Job:
        """Extract job page url to Job object"""
        pass
    
    def get_jobs(self, query: str, location: str) -> list[Job]:
        links = self.lookup(query=query, location=location)
        jobs = []
        for link in links:
            jobs.append(self.extract_job(link))
        return jobs