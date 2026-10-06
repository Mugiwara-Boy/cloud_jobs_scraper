import asyncio
import aiohttp
import json
import urllib.request
import re

async def fetch_jobs(session, url, company, ats_type):
    try:
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
                return results
    except Exception:
        return []
    return []

async def main():
    print("Fetching company lists...")
    gh_req = urllib.request.urlopen(urllib.request.Request("https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data/greenhouse_companies.json", headers={"User-Agent": "Mozilla/5.0"}))
    lv_req = urllib.request.urlopen(urllib.request.Request("https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data/lever_companies.json", headers={"User-Agent": "Mozilla/5.0"}))
    gh_companies = json.loads(gh_req.read().decode())
    lv_companies = json.loads(lv_req.read().decode())
    
    tasks = []
    print(f"Loaded {len(gh_companies) + len(lv_companies)} companies. Scanning...")
    
    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        for c in gh_companies:
            url = f"https://boards-api.greenhouse.io/v1/boards/{c}/jobs"
            tasks.append(fetch_jobs(session, url, c, "greenhouse"))
        for c in lv_companies:
            url = f"https://api.lever.co/v0/postings/{c}"
            tasks.append(fetch_jobs(session, url, c, "lever"))
            
        results = await asyncio.gather(*tasks)
        
    try:
        with open('history.json', 'r') as f:
            history = json.load(f)
    except:
        history = []

    new_jobs = []
    for r in results:
        for j in r:
            match = re.search(r'([A-Za-z0-9-]+)/?$', j['url'])
            if match:
                job_id = match.group(1)
                if job_id not in history:
                    new_jobs.append(j)
                    history.append(job_id)

    # Save updated history
    with open('history.json', 'w') as f:
        json.dump(history, f)
        
    print(f"Found {len(new_jobs)} NEW jobs!")
    
    # Write to LATEST_JOBS.md for Claude to pick up
    with open('LATEST_JOBS.md', 'w') as f:
        f.write("# LATEST JOBS TO BE PROCESSED BY CLAUDE\n\n")
        if not new_jobs:
            f.write("No new jobs today.\n")
        else:
            for j in new_jobs:
                f.write(f"- {j['company']}: {j['title']} | {j['url']}\n")

if __name__ == "__main__":
    asyncio.run(main())
