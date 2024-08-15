## Bitbucket to GitHub Migration Assistant
Welcome to the EC Solutions migration assistant for transferring repositories from Bitbucket to GitHub. This tool was developed since we ourselves started using GitHub instead of Bitbucket and had years worth of repositories, but could not find any publicly available tools to migrate them.

### Installation
To get started, simply clone the repository and open a terminal in the root directory of the repository.

#### Set up virtual environment
The second step is to set up the virtual environment. We assume that you already have a recent version of Python 3.X installed, and can run the following command:
```shell
python3 -m venv venv
```

#### Activate virtual environment and install requirements
```shell
source ./venv/bin/activate
pip install -r requirements.txt
```

### Configuration
In order to function, the application needs access to Bitbucket and Github, as well as a whitelist of the repositories that you actually want to migrate. All of this is stored within the `config.toml` file that can be created from the sample using the following command:
```shell
cp config.toml.sample config.toml
```

#### Bitbucket credentials
Inside the config file you are presented with the following Bitbucket credentials.
* **username**: Your Bitbucket username
* **app_password**: An [app password](https://bitbucket.org/account/settings/app-passwords/) created through the Bitbucket web console. 
* **organisation**: The slug of the workspace containing the repositories you want to transfer. In our case the slug was `ecsolutions`.
> The app password only needs `read` permissions for `Workspace membership` and `Repositories`.

#### GitHub credentials
Inside the config file you are presented with the following GitHub credentials.
* **username**: Your GitHub username
* **access_token**: A [fine-grained personal access token](https://github.com/settings/tokens?type=beta) with access to the GitHub organisation.
* **organisation**: The slug of the destination organisation you want to transfer the repos to. In our case the slug is `ec-ecsolutions`.
> The access token only needs `Read access to metadata` and `Read and Write access to administration and code`.

#### Repositories to transfer
In the `[migration]` section of the config file you also need to define the repositories that you want to transfer.
```
repositories = [
    { name = "old-repo-slug" },
    { name = "old-repo-slug", rename_to = "new-repo-slug" },
]
```
Each repository that you want to transfer should be defined in its own object and line. There is also an optional property called `rename_to` that can be used in case you want your migrated repository to have a updated name.

You also have the option to change the `temp_folder` where the mirrored repositories are temporarily stored. I opted for `/tmp` and I don't see any reason to change it. But you can if you want!

### Running the assistant
Once configured, assuming you're in the virtual environment, the assistant can be started using the following command:
```shell
python main.py config.toml
```
> The config file path is the one and only parameter, and you can move the config file outside the repo if you so wish.


### Enjoy, and contribute if you please! 🤘
