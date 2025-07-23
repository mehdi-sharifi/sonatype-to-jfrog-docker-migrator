# 🐳 Docker Image Migrator

A parallel migration tool to move Docker images from a **Nexus registry** to **Artifactory** using [`crane`](https://github.com/google/go-containerregistry).

---

## 🚀 Features

- Fetches image manifests from Nexus and Artifactory
- Compares images and identifies which are missing in Artifactory
- Uses `crane cp` to copy Docker images in parallel
- Supports retry logic and error logging
- Runs from local or Dockerized environment

---

## 📦 Requirements

- Python 3.7+
- [`crane`](https://github.com/google/go-containerregistry) CLI installed
- Access to both source (Nexus) and destination (Artifactory) registries
- Docker installed (optional, for running in container)

---

## 📁 Project Structure
sonatype-to-jfrog-docker-migrator/

├── main.py                       # 🔁 Main migration script

├── Dockerfile                    # 🐳 Docker image for running the tool

├── requirements.txt              # 📦 Python dependencies (tqdm, requests)

├── .env.sample                   # 🧪 Sample environment config

├── .gitignore                    # 🙈 Ignore logs and secrets # 📄 List of missing images (generated)

└── README.md                     # 📘 Project documentation
## ⚙️ Setup
1. Clone the repo:
```bash
   
git clone https://github.com/mehdi-sharifi/sonatype-to-jfrog-docker-migrator.git
cd sonatype-to-jfrog-docker-migrator
 ```
2. Install dependencies:

```bash

pip install -r requirements.txt
```
3. Set up your .env file (see .env.sample for reference):
```bash

cp .env.sample .env
```
## 🛠 Usage
### ▶️ Run Locally:
```bash

export $(cat .env | xargs)
python main.py
```
## 🐳 Run with Docker
### Build the image
```bash

docker build -t docker-image-migrator .
```
### Run the container
```bash

docker run --rm \
  --env-file .env \
  docker-image-migrator

```
## 🧪 What It Does
- Fetches all Docker images from:

  - Nexus (via REST API)

  - Artifactory (via AQL query)

- Compares image tags and paths

- Saves missing images to not_found_images.log

- Copies them with:

```bash

crane cp --insecure <source> <target>
```
## 📝 Sample .env
```dotenv
# Nexus (source) repository
NEXUS_REPO=reg.example.com
NEXUS_API=http://repo.example.com/service/rest/v1/components?repository=reg.example.com
# Artifactory (destination) configuration
ARTIFACTORY_USER=your_artifactory_username
ARTIFACTORY_PASSWORD=your_artifactory_password
ARTIFACTORY_REPO=docker-repo-hosted
DEST_REPO=artifactory.example.com/target-namespace

# Config 
MAX_WORKER=6
MAX_RETRY=3
RETRY_DELAY=3
```
## 🗃 Logs
- ❌ Errors: migration_errors.log

- 📄 Not found: not_found_images.log

## 🙋 FAQ
- Q: What if crane cp fails?

  - The script retries 3 times per image by default. You can change this via max_retries.

- Q: Can I customize the image list?

    - Yes, modify or provide a different file instead of not_found_images.log.

