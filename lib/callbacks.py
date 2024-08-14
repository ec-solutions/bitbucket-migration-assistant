import os
import typer


def value_is_valid(value, allowed_values):
    if value not in allowed_values:
        raise typer.BadParameter(f"Only the following values are supported: {", ".join(allowed_values)}")
    return value


def verify_path(path: str):
    if not os.path.exists(path):
        raise typer.BadParameter(f"The provided path ({path}) does not exist.")
    return path
