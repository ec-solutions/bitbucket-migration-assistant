import tomllib
from pathlib import Path
from types import SimpleNamespace

_config: "Config"


class Bitbucket(SimpleNamespace):
    username: str
    app_password: str
    organisation: str


class GitHub(SimpleNamespace):
    username: str
    access_token: str
    organisation: str


class Repository(SimpleNamespace):
    name: str
    rename_to: str


class BitbucketRepository(SimpleNamespace):
    name: str
    created_on: str
    description: str
    url: str


class Config(SimpleNamespace):
    bitbucket: Bitbucket
    github: GitHub
    temp_folder: str
    repositories: list[Repository]


def load_config(file):
    global _config
    with open(file, "rb") as toml_data:
        data = tomllib.load(toml_data)

    _config = Config(
        bitbucket=Bitbucket(**data["bitbucket"]),
        github=GitHub(**data["github"]),
        temp_folder=Path(data["migration"]["temp_folder"]),
        repositories=[Repository(**x) for x in data["migration"]["repositories"]],
    )


def get_config():
    return _config
