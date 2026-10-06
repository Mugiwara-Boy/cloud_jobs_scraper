import asyncio
import aiohttp
import json
import urllib.request
import re

async def fetch_jobs(session, company, ats_type):
    try:
        if ats_type == "greenhouse":
            url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
        elif ats_type == "lever":
            url = f"https://api.lever.co/v0/postings/{company}"
        elif ats_type == "ashby":
            url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
        elif ats_type == "smartrecruiters":
            url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings"
        else:
            return []

        async with session.get(url, timeout=5) as response:
            if response.status == 200:
                data = await response.json()
                results = []
                
                if ats_type == "greenhouse":
                    for job in data.get('jobs', []):
                        t = job.get('title', '').lower()
                        if re.search(r'\b(event|events|field marketing|experiential)\b', t):
                            results.append({
                                'company': company.upper(),
                                'title': job.get('title'),
                                'url': job.get('absolute_url')
                            })
                elif ats_type == "lever":
                    for job in data:
                        t = job.get('text', '').lower()
                        if re.search(r'\b(event|events|field marketing|experiential)\b', t):
                            results.append({
                                'company': company.upper(),
                                'title': job.get('text'),
                                'url': job.get('hostedUrl')
                            })
                elif ats_type == "ashby":
                    for job in data.get('jobs', []):
                        t = job.get('title', '').lower()
                        if re.search(r'\b(event|events|field marketing|experiential)\b', t):
                            results.append({
                                'company': company.upper(),
                                'title': job.get('title'),
                                'url': job.get('jobUrl')
                            })
                elif ats_type == "smartrecruiters":
                    for job in data.get('content', []):
                        t = job.get('name', '').lower()
                        if re.search(r'\b(event|events|field marketing|experiential)\b', t):
                            results.append({
                                'company': company.upper(),
                                'title': job.get('name'),
                                'url': f"https://jobs.smartrecruiters.com/{company}/{job.get('id')}"
                            })
                return results
    except Exception:
        return []
    return []

async def main():
    print("Fetching company lists...")
    try:
        gh_req = urllib.request.urlopen(urllib.request.Request("https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data/greenhouse_companies.json", headers={"User-Agent": "Mozilla/5.0"}))
        lv_req = urllib.request.urlopen(urllib.request.Request("https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data/lever_companies.json", headers={"User-Agent": "Mozilla/5.0"}))
        gh_companies = json.loads(gh_req.read().decode())
        lv_companies = json.loads(lv_req.read().decode())
    except:
        gh_companies, lv_companies = [], []

    ashby_companies = ["notion", "vercel", "linear", "deel", "anthropic", "scale", "gong", "canva", "figma", "ramp", "rippling", "clickup", "navan", "airtable", "webflow"]
    sr_companies = ["colliers", "bosch", "ikea", "ubisoft", "visa", "square", "twitter", "robiox"]

    # Load custom targeted companies if they exist
    custom = []
    try:
        with open('custom_companies.txt', 'r') as f:
            custom = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        pass
    
    tasks = []
    print("Building ATS scans...")
    
    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Standard lists map 1:1 to their ATS to save requests
        for c in gh_companies:
            tasks.append(fetch_jobs(session, c, "greenhouse"))
        for c in lv_companies:
            tasks.append(fetch_jobs(session, c, "lever"))
        for c in ashby_companies:
            tasks.append(fetch_jobs(session, c, "ashby"))
        for c in sr_companies:
            tasks.append(fetch_jobs(session, c, "smartrecruiters"))
            
        # For custom companies, we brute force all 4 ATS types to find where they host jobs!
        for c in custom:
            tasks.append(fetch_jobs(session, c, "greenhouse"))
            tasks.append(fetch_jobs(session, c, "lever"))
            tasks.append(fetch_jobs(session, c, "ashby"))
            tasks.append(fetch_jobs(session, c, "smartrecruiters"))
            
        print(f"Executing {len(tasks)} API requests...")
        results = await asyncio.gather(*tasks)
        
    try:
        with open('history.json', 'r') as f:
            history = json.load(f)
    except:
        history = []

    new_jobs = []
    for r in results:
        if r:
            for j in r:
                # Extract ID from URL for deduplication
                match = re.search(r'([A-Za-z0-9-]+)/?$', j['url'])
                if match:
                    job_id = match.group(1)
                    if job_id not in history:
                        new_jobs.append(j)
                        history.append(job_id)

    with open('history.json', 'w') as f:
        json.dump(history, f)
        
    print(f"Found {len(new_jobs)} NEW jobs!")
    
    with open('LATEST_JOBS.md', 'w') as f:
        f.write("# LATEST JOBS TO BE PROCESSED BY CLAUDE\n\n")
        if not new_jobs:
            f.write("No new jobs today.\n")
        else:
            for j in new_jobs:
                f.write(f"- {j['company']}: {j['title']} | {j['url']}\n")

if __name__ == "__main__":
    asyncio.run(main())
