from pathlib import Path
from typing import Annotated

import typer
from alive_progress import alive_bar
from rich import print

from lib import callbacks, helpers


def main(
    config_file: Annotated[Path, typer.Argument(help="The path of the configuration file")],
    temp_folder: Annotated[Path, typer.Argument(help="The path of the temporary migration folder")],
):
    """
    This application is a migration assistant for transferring repositories from BitBucket to your GitHub organisation.
    """

    print("Welcome to the [bold green]Bitbucket to GitHub Migration Tool[/bold green]!")
    print(f"Provided configuration file: {config_file}")
    print(f"Provided temporary folder: {temp_folder}")

    config = helpers.parse_config(config_file)

    print("\n[cyan]Attempting to retrieve all BitBucket repositories...")
    with alive_bar(None, bar="classic", enrich_print=False) as bar:
        repositories = helpers.get_bitbucket_repositories(
            config['bitbucket']['username'],
            config['bitbucket']['app_password'],
            config['bitbucket']['organisation']
        )

        if len(repositories) > 0:
            print(f"Found a total of {len(repositories)} repositories on the {config['bitbucket']['organisation']} workspace.")
        else:
            print("Unfortunately, no repositories could be found.")

        bar()

    if len(repositories) > 0:
        filtered_repos = helpers.filter_repositories(repositories, config["migration"]["repositories"])
        print(f"\n[cyan]Processing repositories. Only {len(filtered_repos)} slated for migration...[/cyan]")
        with alive_bar(len(filtered_repos), bar="classic", enrich_print=True) as bar:
            for repo in filtered_repos:
                bar.text = repo["name"]

                bar()


if __name__ == "__main__":
    typer.run(main)



