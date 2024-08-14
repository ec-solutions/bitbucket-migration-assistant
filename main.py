from pathlib import Path
from typing import Annotated

import time
import typer
from rich import print
import concurrent.futures
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, MofNCompleteColumn

from lib import callbacks, helpers
from lib.config import load_config, get_config


def main(
    config_file: Annotated[Path, typer.Argument(help="The path of the configuration file")],
    temp_folder: Annotated[Path, typer.Argument(help="The path of the temporary migration folder")],
):
    """
    This application is a migration assistant for transferring repositories from BitBucket to your GitHub organisation.
    """
    load_config(config_file)
    config = get_config()

    print("Welcome to the [bold green]Bitbucket to GitHub Migration Tool[/bold green]!")
    print(f"Provided configuration file: {config_file}")
    print(f"Provided temporary folder: {temp_folder}")

    progress_columns = (
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
    )

    print("\n[cyan]Attempting to retrieve all BitBucket repositories...")
    with Progress(*progress_columns) as progress:
        fetching = progress.add_task("", total=None)

        repositories = helpers.get_bitbucket_repositories()
        progress.update(fetching, completed=1, total=1)

    if len(repositories) > 0:
        print(f"Found a total of {len(repositories)} repositories on the {config.bitbucket.organisation} workspace.")
    else:
        print("Unfortunately, no repositories could be found.")

    if len(repositories) > 0:
        whitelist_names = {x.name for x in config.repositories}
        filtered_repos = [x for x in repositories if x.name in whitelist_names]

        print(f"\n[cyan]Processing repositories. Only {len(filtered_repos)} slated for migration...[/cyan]")
        with Progress(MofNCompleteColumn(), *progress_columns) as progress:
            migration = progress.add_task("", total=len(filtered_repos))
            with concurrent.futures.ThreadPoolExecutor() as executor:
                for repo in filtered_repos:
                    executor.submit(helpers.migrate_repository, repo, progress)
                    progress.advance(migration)


if __name__ == "__main__":
    typer.run(main)
