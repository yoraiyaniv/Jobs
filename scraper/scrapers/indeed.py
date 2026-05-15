from playwright.sync_api import sync_playwright

from ..job import Job, JobScraper


BASE_URL = "https://il.indeed.com"

class IndeedScraper(JobScraper):
    def lookup(self, query: str, location: str, num_jobs: int) -> list[str]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # headless=False avoids most blocks
            page = browser.new_page()
            
            url = f"{BASE_URL}/jobs?q={query}&l={location}"
            page.goto(url)
            page.wait_for_timeout(2000)
            
            jobs = page.query_selector_all('a[id^="job_"]')[:num_jobs]
            links = [f"{BASE_URL}{job.get_attribute('href')}" for job in jobs]
            
            browser.close()
            
            return links

    def extract_job(self, url: str) -> Job:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # headless=False avoids most blocks
            page = browser.new_page()

            page.goto(url)
            page.wait_for_timeout(2000)

            # Extract title
            title_elm = page.query_selector('[data-testid="jobsearch-JobInfoHeader-title"]')
            title = title_elm.inner_text() if title_elm else "Unknown"

            # Extract company
            company_elm = page.query_selector('[data-testid="inlineHeader-companyName"]')
            company_name = company_elm.inner_text() if company_elm else "Unknown"
            company_link = None
            if company_elm:
                link_elm = company_elm.query_selector("a")
                company_link = link_elm.get_attribute("href") if link_elm else None

            # Extract location
            location_elm = page.query_selector('[data-testid="jobsearch-JobInfoHeader-companyLocation"]')
            location = location_elm.inner_text() if location_elm else "Unknown"

            # Extract description
            desc_elm = page.query_selector('div[id="jobDescriptionText"]')
            description = desc_elm.inner_text() if desc_elm else "No description available"

            browser.close()

            return Job(title=title,
                       job_link=url,
                       company_name=company_name,
                       company_link=company_link,
                       location=location,
                       description=description)
        
        
if __name__ == "__main__":
    indeed_scraper = IndeedScraper()
    jobs: list[Job] = indeed_scraper.get_jobs("Software Engineer", "Tel Aviv-Jaffa, מחוז תל אביב")
    print(jobs)