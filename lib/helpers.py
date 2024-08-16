import shutil
import requests
import subprocess

from typing import Optional
from rich.progress import Progress
from requests.auth import HTTPBasicAuth

from lib.config import BitbucketRepository
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
    repo_name = next(x.rename_to for x in config.repositories if x.name == repository.name) or repository.name

    # TODO: Validate if repo_name already exists on GitHub...
    task = progress.add_task(repository.name, status="cloning", total=5)

    if repo_path.exists():
        progress.update(task, status="[bold cyan]skipping[/bold cyan]", completed=5)
        return

    # Clone repository
    subprocess.run(["git", "clone", "--mirror", repository.url, repo_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Create repository on GitHub
    progress.update(task, status="preparing", advance=1)
    response = requests.post(
        f"https://api.github.com/orgs/{config.github.organisation}/repos",
        headers={
            "Authorization": f"Bearer {config.github.access_token}",
            "Accept": "application/vnd.github+json"
        },
        json={
            "name": repo_name,
            "description": repository.description,
            "private": True,
        }
    )

    if not response.ok:
        # print(f"Failed to create GitHub repository with the following message: {response.content}")
        if response.status_code == 422:
            progress.update(task, status="[bold red]repo already exists[/bold red]")
        else:
            progress.update(task, status="[bold red]permission error[/bold red]")
        return

    # Migrate repository to GitHub
    progress.update(task, status="migrating", advance=1)
    remote_url = response.json()["clone_url"].replace("https://", f"https://{config.github.username}:{config.github.access_token}@")
    subprocess.run(["git", "remote", "add", "github", remote_url], cwd=repo_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "push", "github", "--all"], cwd=repo_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Verify that the repository now has content
    progress.update(task, status="verifying", advance=1)
    response = requests.get(
        f"https://api.github.com/repos/{config.github.organisation}/{repo_name}",
        headers={
            "Authorization": f"Bearer {config.github.access_token}",
            "Accept": "application/vnd.github+json"
        }
    )

    if not response.ok:
        progress.update(task, status="[bold red]failed to verify[/bold red]")
        return

    if response.json()["size"] > 0:
        progress.update(task, status="[bold green]verified[/bold green]")
    else:
        progress.update(task, status="[bold red]empty repo[/bold red]")

    # Cleaning up
    progress.update(task, status="cleaning", advance=1)
    shutil.rmtree(repo_path, ignore_errors=True)

    # Success!
    progress.update(task, status="[bold green]completed[/bold green]", advance=1)
