import tomllib
import requests
import subprocess
from pathlib import Path
from typing import Optional
from rich import print
from rich.progress import Progress
from requests.auth import HTTPBasicAuth

from lib.config import Repository, BitbucketRepository
from lib.config import get_config


def get_bitbucket_page(request_url: str, authentication: HTTPBasicAuth):
    response = requests.get(request_url, auth=authentication)
    if response.status_code == requests.codes.ok:
        return response.json()
    else:
        return False


def get_bitbucket_repositories() -> list[BitbucketRepository]:
    bitbucket = get_config().bitbucket

    repositories: list[BitbucketRepository] = []
    authentication = HTTPBasicAuth(bitbucket.username, bitbucket.app_password)
    request_url = f"https://api.bitbucket.org/2.0/repositories/{bitbucket.organisation}/?pagelen=100"

    while True:
        response = get_bitbucket_page(request_url, authentication)
        if response is False:
            break

        for repo in response["values"]:
            repositories.append(BitbucketRepository(
                name=repo["slug"],
                created_on=repo["created_on"],
                description=repo["description"],
                url=f"https://{bitbucket.username}:{bitbucket.app_password}@bitbucket.org/{bitbucket.organisation}/{repo["slug"]}.git"
            ))

        if "next" not in response:
            break

        request_url = response["next"]

    return repositories


def migrate_repository(repository: BitbucketRepository, progress: Optional[Progress] = None):
    config = get_config()
    repo_path = config.temp_folder / repository.name
    task = progress.add_task(repository.name, status="cloning", total=3)
    subprocess.run(["git", "clone", "--mirror", repository.url, repo_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    progress.update(task, status="preparing GitHub", advance=1)
    response = requests.post(
        f"https://api.github.com/orgs/{config.github.organisation}/repos",
        headers={
            "Authorization": f"Bearer {config.github.access_token}",
            "Accept": "application/vnd.github+json"
        },
        json={
            "name": next(x.rename_to for x in config.repositories if x.name == repository.name) or repository.name,
            "description": repository.description,
            "private": True,
        }
    )

    if not response.ok:
        progress.update(task, status="[bold red]failed[/bold red]")
        # Potential error handling or feedback?
        return

    progress.update(task, status="migrating", advance=1)
    subprocess.run()


    progress.update(task, status="completed", advance=1)
