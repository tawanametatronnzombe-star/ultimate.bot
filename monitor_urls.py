import os
import json
import requests
from bs4 import BeautifulSoup

# Paths
repo_root = os.getcwd()
urls_file = os.path.join(repo_root, "urls.txt")
data_file = os.path.join(repo_root, "url_data.json")
sitemap_file = os.path.join(repo_root, "sitemap.xml")
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

# Update sitemap.xml
urlset = BeautifulSoup(features="xml")
urlset.append(urlset.new_tag("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"))

# Add repo HTML files
for f in os.listdir(repo_root):
    if f.endswith(".html"):
        url_tag = urlset.new_tag("url")
        loc = urlset.new_tag("loc")
        loc.string = f"https://tawanametatronnzombe-star.github.io/Metatron878/{f}"
        url_tag.append(loc)
        urlset.urlset.append(url_tag)

# Add monitored URLs
for url in urls:
    url_tag = urlset.new_tag("url")
    loc = urlset.new_tag("loc")
    loc.string = url
    url_tag.append(loc)
    urlset.urlset.append(url_tag)

with open(sitemap_file, "w", encoding="utf-8") as f:
    f.write(str(urlset.prettify()))
print("✅ Sitemap updated.")

# Create GitHub issues for changed URLs
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

# Auto-commit and push changes
os.system('git config --global user.name "GitHub Actions Bot"')
os.system('git config --global user.email "actions@github.com"')
os.system('git add url_data.json sitemap.xml')
if changes_detected:
    os.system('git commit -m "Auto-update URL data & sitemap due to changes"')
    os.system('git push')

# Auto-deploy GitHub Pages (live)
os.system('git branch -M main')  # ensure main branch
os.system('git push origin main')  # push updates live
print("✅ GitHub Pages deployed live with latest updates!")
