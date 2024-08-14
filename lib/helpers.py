import tomllib
import requests
from requests.auth import HTTPBasicAuth
from rich import print


def parse_config(file) -> dict:
    with open(file, "rb") as toml_data:
        data = tomllib.load(toml_data)

    return data


def extract_repositories(repositories: list) -> list:
    formatted = []
    for repo in repositories:
        formatted.append({
            "name": repo["name"],
            "created_on": repo["created_on"],
            "description": repo["description"],
            # "links": repo["links"],
        })

    return formatted


def get_bitbucket_page(request_url: str, authentication: HTTPBasicAuth):
    response = requests.get(request_url, auth=authentication)
    if response.status_code == requests.codes.ok:
        return response.json()
    else:
        return False


def get_bitbucket_repositories(username: str, password: str, organisation: str,):
    repositories = []
    authentication = HTTPBasicAuth(username, password)
    request_url = f"https://api.bitbucket.org/2.0/repositories/{organisation}/?pagelen=100"
    response = get_bitbucket_page(request_url, authentication)

    if response is not False:
        extract_repositories(response["values"])
        repositories.extend(extract_repositories(response["values"]))
        while "next" in response:
            response = get_bitbucket_page(response["next"], authentication)
            repositories.extend(extract_repositories(response["values"]))

    return repositories


def filter_repositories(repositories: list, whitelist: list):
    whitelist_names = {x["name"] for x in whitelist}
    return [x for x in repositories if x["name"] in whitelist_names]
