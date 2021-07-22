# About

A python script to query the usage of service accounts and service account keys
from a Google Cloud project.

# Requirements

To use this script, the following software needs to be installed:

- Pipenv
- Python 3.9 (or pyenv)
- Google Cloud SDK

# Setup

Install the required python libraries:

```
pipenv sync
```

Authenticate against Google Cloud or supply service account credentials:

```
# This writes Application Default Credentials to a default location
gcloud auth application-default login

# Using service account credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

# Usage

```
pipenv run sa_usage --help
usage: sa_usage.py [-h] --project PROJECT (--hours HOURS | --days DAYS)

List service account usage.

optional arguments:
  -h, --help         show this help message and exit
  --project PROJECT  List service account usage for the specific project
  --hours HOURS      List usage for the last number of hours
  --days DAYS        List usage for the last number of days

pipen run sa_usage --project <your-project> --days 30 |jq '<your-filter>'
```
