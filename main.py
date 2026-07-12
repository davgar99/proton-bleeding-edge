import os
import re
import shutil
import subprocess
from pathlib import Path
from time import sleep
from typing import Any, Callable

RETRY = object()
INPUT_ATTEMPT_LIMIT = 3
BUILD_READY_DELAY_SECONDS = 2
DEFAULT_BUILD_NAME = "my_build"
DEFAULT_INSTALL_DIRECTORY = "proton-bleeding-edge"
GIT_REPO_URL = "https://github.com/ValveSoftware/Proton.git"
GIT_BRANCH = "bleeding-edge"
PROTON_SOURCE_DIRECTORY = "Proton"
PROTON_BUILD_DIRECTORY = "build"
PROTON_DIST_DIRECTORY = "dist"
STEAM_COMPATIBILITYTOOLS_DIRECTORY = ".steam/root/compatibilitytools.d"
NAME_PATTERN = re.compile(r"[A-Za-z0-9._-]+")

Callback = Callable[[], Any]


def no_action() -> None:
    return None


def retry_action() -> object:
    return RETRY


def user_query(
    input_message: str,
    case_y: Callback = no_action,
    case_n: Callback = no_action,
    case_empty: Callback = no_action,
    case_other: Callback = retry_action,
    max_attempts: int = 1,
    fail_message: str = "Invalid input, try again.",
    fallback_message: str = "Too many invalid attempts.",
    fallback_action: Callback = no_action,
) -> Any:
    attempt = 1
    while max_attempts == 0 or attempt <= max_attempts:
        response = input(input_message)
        attempt += 1

        match response.strip().lower():
            case "y":
                result = case_y()
            case "n":
                result = case_n()
            case "":
                result = case_empty()
            case _:
                result = case_other()

        if result != RETRY:
            return result

        if max_attempts == 0 or attempt <= max_attempts:
            print(fail_message)

    print(fallback_message)
    return fallback_action()


def is_valid_name(name: str) -> bool:
    return bool(NAME_PATTERN.fullmatch(name))


def get_name(prompt_message: str, default_name: str) -> str:
    for _ in range(INPUT_ATTEMPT_LIMIT):
        response = input(prompt_message).strip()
        if not response:
            print("Name cannot be empty.")
            continue

        if not is_valid_name(response):
            print("Invalid name. Use letters, digits, '.', '_' or '-' only.")
            continue

        return response

    print(f"Too many invalid attempts.\nUsing default name '{default_name}'.")
    sleep(1)
    return default_name


def prompt_for_build_name(default_name: str) -> str:
    return user_query(
        input_message="Would you like to give this Proton build a custom name? [Y/n] ",
        case_y=lambda: get_name("Please enter the build name: ", default_name),
        case_n=lambda: default_name,
        case_empty=lambda: get_name("Please enter the build name: ", default_name),
        max_attempts=INPUT_ATTEMPT_LIMIT,
        fallback_message=(
            f"Too many invalid attempts.\nUsing default build name '{default_name}'."
        ),
        fallback_action=lambda: default_name,
    )


def prompt_for_install_directory(default_name: str) -> str:
    return user_query(
        input_message="Would you like to give Proton a custom directory name? [Y/n] ",
        case_y=lambda: get_name("Please enter the directory name: ", default_name),
        case_n=lambda: default_name,
        case_empty=lambda: get_name("Please enter the directory name: ", default_name),
        max_attempts=INPUT_ATTEMPT_LIMIT,
        fallback_message=(
            f"Too many invalid attempts.\nUsing default name '{default_name}'."
        ),
        fallback_action=lambda: default_name,
    )


def get_git_revision(source_dir: Path, revision: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", revision],
        cwd=source_dir,
        text=True,
    ).strip()


def prepare_proton_source(workspace_dir: Path) -> Path:
    source_dir = workspace_dir / PROTON_SOURCE_DIRECTORY
    if source_dir.exists():
        print("Proton directory already exists. Fetching remote repository:")
        subprocess.run(
            ["git", "fetch", "--recurse-submodules"],
            cwd=source_dir,
            check=True,
        )
        local_revision = get_git_revision(source_dir, "@")
        remote_revision = get_git_revision(source_dir, "@{u}")

        if local_revision != remote_revision:
            print("Updating your local repository...")
            subprocess.run(
                ["git", "pull", "--recurse-submodules"],
                cwd=source_dir,
                check=True,
            )
        else:
            print("Your local repository is already up to date.")
    else:
        print("Cloning the Proton repository...")
        subprocess.run(
            [
                "git",
                "clone",
                "-b",
                GIT_BRANCH,
                "--recurse-submodules",
                GIT_REPO_URL,
                PROTON_SOURCE_DIRECTORY,
            ],
            cwd=workspace_dir,
            check=True,
        )
        print("Repo has been cloned successfully.")

    sleep(BUILD_READY_DELAY_SECONDS)
    return source_dir


def build_proton(source_dir: Path, build_name: str) -> Path:
    build_dir = source_dir / PROTON_BUILD_DIRECTORY
    build_dir.mkdir(exist_ok=True)
    subprocess.run(
        ["../configure.sh", "--enable-ccache", f"--build-name={build_name}"],
        cwd=build_dir,
        check=True,
    )

    job_count = os.cpu_count() or 1
    print(f"Running make with {job_count} parallel job(s).")
    subprocess.run(["make", f"-j{job_count}", "redist"], cwd=build_dir, check=True)

    print("Proton has finished compiling.")
    return build_dir / PROTON_DIST_DIRECTORY


def install_proton(dist_dir: Path, install_dir: Path) -> None:
    install_dir.parent.mkdir(parents=True, exist_ok=True)
    if install_dir.exists():
        shutil.rmtree(install_dir)

    shutil.copytree(dist_dir, install_dir)
    print(
        "Proton has been moved to your Steam compatibilitytools.d directory as "
        f"{install_dir.name}."
    )


def should_overwrite_installation(proton_dir: str) -> bool:
    return user_query(
        input_message=(
            f"The directory {proton_dir} already exists in Steam "
            "compatibilitytools.d. Would you like to overwrite it? [Y/n] "
        ),
        case_y=lambda: True,
        case_n=lambda: False,
        case_empty=lambda: True,
        max_attempts=INPUT_ATTEMPT_LIMIT,
        fallback_action=lambda: False,
    )


def should_install_proton() -> bool:
    return user_query(
        input_message=(
            "Would you like this script to move the file over to your Steam "
            "compatibilitytools.d directory? [Y/n] "
        ),
        case_y=lambda: True,
        case_n=lambda: False,
        case_empty=lambda: True,
        max_attempts=INPUT_ATTEMPT_LIMIT,
        fallback_action=lambda: False,
    )


def main() -> None:
    workspace_dir = Path.cwd()
    build_name = prompt_for_build_name(DEFAULT_BUILD_NAME)
    source_dir = prepare_proton_source(workspace_dir)
    dist_dir = build_proton(source_dir, build_name)

    proton_dir = prompt_for_install_directory(DEFAULT_INSTALL_DIRECTORY)
    install_dir = Path.home() / STEAM_COMPATIBILITYTOOLS_DIRECTORY / proton_dir

    if install_dir.exists():
        if should_overwrite_installation(proton_dir):
            install_proton(dist_dir, install_dir)
    elif should_install_proton():
        install_proton(dist_dir, install_dir)


if __name__ == "__main__":
    main()
    print("Program will now close.")
