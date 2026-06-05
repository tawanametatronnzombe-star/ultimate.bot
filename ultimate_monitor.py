import os
import json
import requests
from bs4 import BeautifulSoup

# -------- CONFIG --------
GITHUB_USER = "tawanametatronnzombe-star"
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPOS_FILE = "repos.json"
URLS_FILE = "urls.txt"  # Optional external URLs monitoring

headers = {"Authorization": f"token {GITHUB_TOKEN}"}

# -------- SCAN REPOS --------
repos_resp = requests.get(f"https://api.github.com/users/{GITHUB_USER}/repos", headers=headers)
repos = repos_resp.json()

all_repos_data = []

for repo in repos:
    repo_name = repo["name"]
    pages = []

    contents_resp = requests.get(f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}/contents", headers=headers)
    if contents_resp.status_code != 200:
        continue
    contents = contents_resp.json()

    for item in contents:
        if item["name"].endswith(".html"):
            pages.append(item["name"])

    if pages:
        all_repos_data.append({
            "repo_name": repo_name,
            "pages": pages
        })

# Save repos.json
with open(REPOS_FILE, "w", encoding="utf-8") as f:
    json.dump(all_repos_data, f, indent=2)
print(f"✅ repos.json updated with {len(all_repos_data)} repos containing HTML pages")

# -------- MONITOR EXTERNAL URLs --------
changes_detected = []
old_data = {}
if os.path.exists(URLS_FILE):
    if os.path.exists("url_data.json"):
        with open("url_data.json", "r") as f:
            old_data = json.load(f)

    with open(URLS_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    new_data = {}
    for url in urls:
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            title = soup.title.string.strip() if soup.title else "No title"
            desc_tag = soup.find("meta", attrs={"name": "description"})
            description = desc_tag["content"].strip() if desc_tag else "No description"
            new_data[url] = {"title": title, "description": description}

            if url not in old_data or old_data[url] != new_data[url]:
                changes_detected.append(url)
        except Exception as e:
            print(f"❌ Failed to fetch {url}: {e}")

    # Save URL data
    with open("url_data.json", "w") as f:
        json.dump(new_data, f, indent=2)

# -------- CREATE ISSUES FOR CHANGES --------
for url in changes_detected:
    issue_url = f"https://api.github.com/repos/{GITHUB_USER}/ultimate.bot/issues"
    data = {
        "title": f"Content change detected: {url}",
        "body": f"The page content for {url} has changed.\nNew title: {new_data[url]['title']}\nDescription: {new_data[url]['description']}"
    }
    resp = requests.post(issue_url, json=data, headers=headers)
    if resp.status_code == 201:
        print(f"✅ Issue created for {url}")
    else:
        print(f"❌ Failed to create issue for {url}: {resp.json()}")

# -------- AUTO-COMMIT CHANGES --------
os.system('git config --global user.name "GitHub Actions Bot"')
os.system('git config --global user.email "actions@github.com"')
os.system(f'git add {REPOS_FILE} url_data.json')
if changes_detected or all_repos_data:
    os.system('git commit -m "Auto-update repos.json & URL data" || echo "No changes to commit"')
    os.system('git push')

# -------- DEPLOY PAGES LIVE --------
os.system('git branch -M main')
os.system('git push origin main')
print("✅ GitHub Pages deployed live with latest updates!")
