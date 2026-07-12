import os
import re
import subprocess
from time import sleep
from typing import Callable, Tuple

RETRY = object()
MAX_NAME_ATTEMPTS = 3
NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
ALLOWED_NAME_CHARACTERS = "letters, digits, '.', '_', and '-'"

PROTON_DIRECTORY = "Proton"
PROTON_REPOSITORY_URL = "https://github.com/ValveSoftware/Proton.git"
PROTON_BRANCH = "bleeding-edge"
DEFAULT_BUILD_NAME = "my_build"
DEFAULT_PROTON_DIR = "proton-bleeding-edge"
DEFAULT_SLEEP_SECONDS = 1
POST_CLONE_DELAY_SECONDS = 2
MIN_JOB_COUNT = 1
STAGED_DIRECTORY_SUFFIX = ".tmp"
STEAM_COMPATIBILITY_PATH = os.path.join(
    ".steam",
    "root",
    "compatibilitytools.d",
)


def do_nothing() -> None:
    return None


def retry_query() -> object:
    return RETRY


def user_query(
    input_message: str,
    case_y: Callable[[], object] = do_nothing,
    case_n: Callable[[], object] = do_nothing,
    case_empty: Callable[[], object] = do_nothing,
    case_: Callable[[], object] = retry_query,
    max_attempts: int = 1,
    fail_message: str = "Invalid input, try again.",
    fallback_message: str = "Too many invalid attempts.",
    fallback_script: Callable[[], object] = do_nothing,
):
    attempt_count = 0
    while max_attempts == 0 or attempt_count < max_attempts:
        response = input(input_message)
        match response.strip().lower():
            case "y":
                result = case_y()
            case "n":
                result = case_n()
            case "":
                result = case_empty()
            case _:
                result = case_()

        if result != RETRY:
            return result

        attempt_count += 1
        if max_attempts == 0 or attempt_count < max_attempts:
            print(fail_message)

    print(fallback_message)
    return fallback_script()


def is_valid_name(name: str) -> bool:
    if name in {".", ".."}:
        return False

    return bool(NAME_PATTERN.fullmatch(name))


def update_existing_proton_repo() -> None:
    print("Proton directory already exists. Fetching remote repository:")
    os.chdir(PROTON_DIRECTORY)
    subprocess.run(["git", "fetch", "--recurse-submodules"], check=True)
    local = subprocess.check_output(["git", "rev-parse", "@"]).strip()
    remote = subprocess.check_output(["git", "rev-parse", "@{u}"]).strip()

    if local != remote:
        print("Updating your local repository...")
        subprocess.run(["git", "pull", "--ff-only", "--recurse-submodules"], check=True)
    else:
        print("Your local repository is on the latest version already.")

def get_name(input_message: str, default_name: str, label: str) -> str:
    for _ in range(MAX_NAME_ATTEMPTS):
        response = input(input_message).strip()
        if not response:
            print(f"{label} name cannot be empty.")
        elif not is_valid_name(response):
            print(
                f"Invalid {label.lower()} name. "
                f"Use {ALLOWED_NAME_CHARACTERS} only."
            )
        else:
            return response

    print(
        "Too many invalid attempts.\n"
        f"Using default name '{default_name}'."
    )
    sleep(DEFAULT_SLEEP_SECONDS)
    return default_name


def get_build_and_proton_dir(
    default_build_name: str,
    default_dir_name: str,
) -> Tuple[str, str]:
    """Prompt for both custom names before the build starts, with defaults as fallbacks."""
    build_name = get_name("Please enter the build name: ", default_build_name, "Build")
    proton_dir = get_name(
        "Please enter the directory name: ",
        default_dir_name,
        "Directory",
    )
    return build_name, proton_dir


def move_proton_dir(
    home_dir: str,
    proton_dir: str,
    proton_dir_exists: bool,
) -> None:
    compatibilitytools_dir = os.path.join(home_dir, STEAM_COMPATIBILITY_PATH)
    target_dir = os.path.join(compatibilitytools_dir, proton_dir)
    staged_dir = f"{target_dir}{STAGED_DIRECTORY_SUFFIX}"

    if os.path.exists(staged_dir):
        subprocess.run(["rm", "-rf", staged_dir], check=True)
    subprocess.run(["cp", "-r", "redist", staged_dir], check=True)
    if proton_dir_exists:
        subprocess.run(["rm", "-rf", target_dir], check=True)
    subprocess.run(["mv", staged_dir, target_dir], check=True)
    print(
        "Proton has been moved to your Steam compatibilitytools.d directory "
        f"as {proton_dir}."
    )


def main() -> None:
    home_dir = os.path.expanduser("~")

    if os.path.exists(PROTON_DIRECTORY):
        update_existing_proton_repo()
    else:
        print("Cloning the Proton repository...")
        subprocess.run(
            [
                "git",
                "clone",
                "-b",
                PROTON_BRANCH,
                "--recurse-submodules",
                PROTON_REPOSITORY_URL,
            ],
            check=True,
        )
        os.chdir(PROTON_DIRECTORY)
        print("Repo has been cloned successfully.")

    sleep(POST_CLONE_DELAY_SECONDS)

    def prompt_for_custom_names() -> Tuple[str, str]:
        return get_build_and_proton_dir(
            DEFAULT_BUILD_NAME,
            DEFAULT_PROTON_DIR,
        )
    build_name, proton_dir = user_query(
        input_message="Would you like to give Proton custom build and directory names? [Y/n] ",
        case_y=prompt_for_custom_names,
        case_n=lambda: (DEFAULT_BUILD_NAME, DEFAULT_PROTON_DIR),
        case_empty=prompt_for_custom_names,
        case_=retry_query,
        max_attempts=MAX_NAME_ATTEMPTS,
        fallback_message=(
            "Too many invalid attempts.\n"
            f"Using default names '{DEFAULT_BUILD_NAME}' and '{DEFAULT_PROTON_DIR}'."
        ),
        fallback_script=lambda: (DEFAULT_BUILD_NAME, DEFAULT_PROTON_DIR),
    )

    os.makedirs("build", exist_ok=True)
    os.chdir("build")
    subprocess.run(
        ["../configure.sh", "--enable-ccache", f"--build-name={build_name}"],
        check=True,
    )

    job_count = os.cpu_count() or MIN_JOB_COUNT
    print(f"Creating Jobs: {job_count} created")
    subprocess.run(["make", f"-j{job_count}", "redist"], check=True)

    print("Proton has finished compiling.")

    proton_dir_exists = os.path.exists(
        os.path.join(home_dir, STEAM_COMPATIBILITY_PATH, proton_dir)
    )

    if proton_dir_exists:
        user_query(
            input_message=(
                f"The directory {proton_dir} already exists in Steam compatibilitytools.d. "
                "Would you like to overwrite it? [Y/n] "
            ),
            case_y=lambda: move_proton_dir(home_dir, proton_dir, proton_dir_exists),
            case_empty=lambda: move_proton_dir(home_dir, proton_dir, proton_dir_exists),
            max_attempts=MAX_NAME_ATTEMPTS,
        )
    else:
        user_query(
            input_message=(
                "Would you like this script to move the build to your "
                "Steam compatibilitytools.d directory? [Y/n] "
            ),
            case_y=lambda: move_proton_dir(home_dir, proton_dir, proton_dir_exists),
            case_empty=lambda: move_proton_dir(home_dir, proton_dir, proton_dir_exists),
            max_attempts=MAX_NAME_ATTEMPTS,
        )


if __name__ == "__main__":
    main()
    print("Program will now close.")
