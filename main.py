import logging
import urllib3
import requests
import threading
import subprocess
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Suppress warnings for insecure HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurable variables (use environment variables or .env file in dev)
REPO_NAME = os.getenv("NEXUS_REPO", "source.repo.com")
BASE_URL = os.getenv("NEXUS_API", f"http://source.repo.com/service/rest/v1/components?repository={REPO_NAME}")
ARTIFACTORY_USER = os.getenv("ARTIFACTORY_USER", "your_username")
ARTIFACTORY_PASSWORD = os.getenv("ARTIFACTORY_PASSWORD", "your_password")
ARTIFACTORY_REPO = os.getenv("ARTIFACTORY_REPO", "docker-repo-hosted")
DEST_REPO = os.getenv("DEST_REPO", "artifactory.repo.com/target")
MAX_WORKER = os.getenv("MAX_WORKER", 5)
MAX_RETRY = os.getenv("MAX_RETRY", 3)
RETRY_DELAY= os.getenv("RETRY_DELAY", 5)
# Logging
LOG_FILE = "migration_errors.log"
NOT_FOUND_LOG = "not_found_images.log"
logging.basicConfig(
    filename=LOG_FILE,
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.ERROR
)

rmi_lock = threading.Lock()

def get_docker_images_from_artifactory():
    images = set()
    url = f"https://{DEST_REPO.split('/')[0]}/artifactory/api/search/aql"
    payload = f'''
items.find({{
  "repo": "{ARTIFACTORY_REPO}",
  "name": "manifest.json"
}}).include("repo","path","name","created","modified")
'''
    headers = {'Content-Type': 'text/plain'}
    response = requests.post(url, headers=headers, data=payload,
                             auth=(ARTIFACTORY_USER, ARTIFACTORY_PASSWORD), verify=False)

    if response.status_code != 200:
        raise Exception(f"Error {response.status_code}: {response.text}")

    for item in response.json().get("results", []):
        path = item["path"].strip("/")
        parts = path.split("/")
        if len(parts) < 2:
            continue
        tag = parts[-1]
        name = "/".join(parts[:-1])
        full_image = f"{REPO_NAME}/{name}:{tag}"
        images.add(full_image)

    return images

def get_docker_images_from_nexus():
    continuation_token = None
    images = set()

    while True:
        url = BASE_URL
        if continuation_token:
            url += f"&continuationToken={continuation_token}"

        response = requests.get(url, verify=False)
        if response.status_code != 200:
            break

        data = response.json()
        for item in data.get("items", []):
            name = item.get("name")
            version = item.get("version")
            if not name or not version:
                continue
            full_image = f"{REPO_NAME}/{name}:{version}"
            images.add(full_image)

        continuation_token = data.get("continuationToken")
        if not continuation_token:
            break

    return images

def to_migrate(nexus_images, artifactory_images):
    diff = sorted(nexus_images - artifactory_images)
    with open(NOT_FOUND_LOG, 'w') as nf:
        for image in diff:
            nf.write(image + "\n")
    return diff

def crane_copy_with_retry(image, max_retries=MAX_RETRY, retry_delay=RETRY_DELAY):
    new_image = image.replace(REPO_NAME, DEST_REPO)
    print(f"🔄 Copying {image} -> {new_image}")

    for attempt in range(1, max_retries + 1):
        try:
            subprocess.run(["crane", "cp", "--insecure", image, new_image], check=True)
            print(f"✅ Successfully copied {image}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Attempt {attempt} failed for {image}: {e}")
            if attempt == max_retries:
                print(f"❌ Giving up on {image}")
            else:
                time.sleep(retry_delay)
    return False

def migrate_with_crane_parallel(filename, max_workers=8, max_retries=MAX_RETRY, retry_delay=5):
    try:
        with open(filename, "r") as f:
            lines = f.readlines()

        images = sorted(set(line.strip() for line in lines if line.strip()))
        print(f"📦 Found {len(images)} images to migrate.")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(crane_copy_with_retry, image, max_retries, RETRY_DELAY): image
                for image in images
            }

            for future in as_completed(futures):
                image = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"💥 Unexpected error copying {image}: {e}")

    except FileNotFoundError:
        print(f"🚫 File not found: {filename}")

def main():
    print("📡 Fetching Artifactory images...")
    artifactory_images = get_docker_images_from_artifactory()
    print(f"✅ Found {len(artifactory_images)} Artifactory images")

    print("📡 Fetching Nexus images...")
    nexus_images = get_docker_images_from_nexus()
    print(f"✅ Found {len(nexus_images)} Nexus images")

    print("🔍 Comparing...")
    not_exist = to_migrate(nexus_images, artifactory_images)
    print(f"❗ {len(not_exist)} images not found in Artifactory")
    for img in not_exist[:10]:
        print(f" - {img}")
    if len(not_exist) > 10:
        print("... (see full list in not_found_images.log)")

if __name__ == "__main__":
    main()
    migrate_with_crane_parallel("not_found_images.log", max_workers=MAX_WORKER, max_retries=MAX_RETRY, retry_delay=RETRY_DELAY)