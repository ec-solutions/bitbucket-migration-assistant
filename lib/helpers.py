import re
import sys
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

    task = progress.add_task(repository.name, status="cloning", total=5)

    # Verify the repo doesn't already exist on GitHub
    response = requests.get(
        f"https://api.github.com/repos/{config.github.organisation}/{repo_name}",
        headers={
            "Authorization": f"Bearer {config.github.access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
    empty_repo_already_created = False
    if response.status_code != 404:
        # Repo _does_ exist; must be empty to go forth
        if response.json()["size"] == 0:
            empty_repo_already_created = True
        else:
            print(f"Non-empty GitHub repo {repo_name!r} already exists.\n", file=sys.stderr)
            progress.update(task, status="[bold red]already exists[/]", total=None)
            return
    elif not response.ok:
        # just ignore it, probably expected, and we'll try to create it later
        pass

    # Clone repository
    clone_cmd = (
       ["git", "clone", "--mirror", repository.url, repo_path]
       if not repo_path.exists() else
       ["git", "-C", repo_path, "remote", "update"]
    )

    try:
        subprocess.run(
            clone_cmd,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Clone of {repository.name!r} failed with error:", e.stderr or "<no output>", file=sys.stderr)
        progress.update(task, status="[bold red]clone error[/]", completed=5)
        return

    # Check if repo contains files above GitHub file size limits and would require Git LFS
    p = subprocess.run(
        "git rev-list --objects --all"  # Intentional lack of comma to join strings
        "| git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)'",
        shell=True,
        capture_output=True,
        text=True,
        cwd=repo_path,
    )
    files = []
    for match in re.finditer(r"(.*?) (.*?) (.*?)(?: (.*))?(?:\n|$)", p.stdout):
        type_, object_name, size, file_path = match.groups()
        if type_ == "blob":
            files.append((object_name, int(size), file_path))

    github_file_size_limit = 100 * 2**20  # 100 MiB
    if any(size > github_file_size_limit for _, size, _ in files):
        print(f"Repo {repository.name!r} contains files over 100 MiB GitHub limit; Git LFS required.", file=sys.stderr)
        progress.update(task, status="[bold red]Git LFS required[/]", completed=5)
        # TODO: handle repos requiring Git LFS
        # git lfs migrate import --everything
        return

    # Create repository on GitHub
    if not empty_repo_already_created:
        response = requests.post(
            f"https://api.github.com/orgs/{config.github.organisation}/repos",
            headers={
                "Authorization": f"Bearer {config.github.access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
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
                # TODO: Repos have failed because of newlines in description. Needs general error handling...
                progress.update(task, status="[red]error 422[/red]")
            else:
                progress.update(task, status="[red]permission error[/red]")
            return

    # Migrate repository to GitHub
    progress.update(task, status="migrating", advance=1)
    remote_url = response.json()["clone_url"].replace("https://", f"https://{config.github.username}:{config.github.access_token}@")

    subprocess.run(["git", "remote", "add", "github", remote_url], cwd=repo_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        subprocess.run(["git", "push", "github", "--all"], cwd=repo_path, check=True, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Push {repository.name!r} -> {repo_name!r} failed with error:\n", e.stderr, file=sys.stderr)
        progress.update(task, status="[bold red]push error[/]", completed=5)
        return

    # TODO: Add support for archiving repo based on config archive = true...

    # Cleaning up
    progress.update(task, status="cleaning", advance=1)
    shutil.rmtree(repo_path, ignore_errors=True)

    # Success!
    progress.update(task, status="[bold green]completed[/bold green]", advance=1)
