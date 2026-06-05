import os
import json
import requests
from bs4 import BeautifulSoup

repo_root = os.getcwd()
urls_file = os.path.join(repo_root, "urls.txt")
data_file = os.path.join(repo_root, "url_data.json")
token = os.environ["GITHUB_TOKEN"]
repo = os.environ["REPO"]

# Load previous URL data
if os.path.exists(data_file):
    with open(data_file, "r", encoding="utf-8") as f:
        old_data = json.load(f)
else:
    old_data = {}

# Read URLs
with open(urls_file, "r") as f:
    urls = [line.strip() for line in f if line.strip()]

new_data = {}
changes_detected = []

# Fetch URL info
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

# Save updated URL data
with open(data_file, "w", encoding="utf-8") as f:
    json.dump(new_data, f, indent=2)

# Create GitHub issues for changes
for url in changes_detected:
    issue_url = f"https://api.github.com/repos/{repo}/issues"
    data = {
        "title": f"Content change detected: {url}",
        "body": f"The page content for {url} has changed.\nNew title: {new_data[url]['title']}\nDescription: {new_data[url]['description']}"
    }
    headers = {"Authorization": f"token {token}"}
    resp = requests.post(issue_url, json=data, headers=headers)
    if resp.status_code == 201:
        print(f"✅ Issue created for {url}")
    else:
        print(f"❌ Failed to create issue for {url}: {resp.json()}")

# Auto-commit URL data
os.system('git config --global user.name "GitHub Actions Bot"')
os.system('git config --global user.email "actions@github.com"')
os.system('git add url_data.json')
if changes_detected:
    os.system('git commit -m "Auto-update URL data due to changes"')
    os.system('git push')

# Auto-deploy to GitHub Pages
os.system('git branch -M main')  # ensure main branch
os.system('git push origin main')  # push updates live
print("✅ GitHub Pages deployed live with latest updates!")
