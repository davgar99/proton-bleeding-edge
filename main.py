import os
import re
import subprocess
from time import sleep
from typing import Callable, Tuple

# -- Global Variables --

RETRY = object()
MAX_NAME_ATTEMPTS = 3
NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
ALLOWED_NAME_CHARACTERS = "letters, digits, '.', '_', and '-'"

# -- Helper functions --

def user_query(
        input_message: str,
        case_y: Callable[[], object] = lambda: None, 
        case_n: Callable[[], object] = lambda: None,
        case_empty: Callable[[], object] = lambda: None,
        case_: Callable[[], object] = lambda: RETRY,
        max_attempts: int = 1,
        fail_message: str = "Invalid input, try again.",
        fallback_message: str = "Too many invalid attempts.",
        fallback_script: Callable[[], object] = lambda: None
        ):
    attempt = 1
    while max_attempts == 0 or attempt <= max_attempts:
        attempt += 1
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
        
        if max_attempts == 0 or attempt <= max_attempts:
            print(fail_message)
    print(fallback_message)
    return fallback_script()

def raise_valueerror(msg):
    raise ValueError(msg)

def is_valid_name(name: str) -> bool:
    return bool(NAME_PATTERN.fullmatch(name))

def update_existing_proton_repo() -> None:
    print("Proton directory already exists. Fetching remote repository:")
    os.chdir("Proton")
    subprocess.run(["git", "fetch", "--recurse-submodules"], check=True)
    local = subprocess.check_output(["git", "rev-parse", "@"]).strip()
    remote = subprocess.check_output(["git", "rev-parse", "@{u}"]).strip()

    if local != remote:
        print("Updating your local repository...")
        subprocess.run(["git", "pull", "--ff-only", "--recurse-submodules"], check=True)
    else:
        print("Your local repository is on the latest version already.")

# -- Primary functions --

def get_proton_dir(default_dir_name: str) -> str:
    return get_name("Please enter the directory name: ", default_dir_name, "Directory")

def get_name(input_message: str, default_name: str, label: str) -> str:
    attempt: int = 1
    while attempt <= MAX_NAME_ATTEMPTS:
        attempt += 1
        response = input(input_message).strip()
        if not response:
            print(f"{label} name cannot be empty.")
            pass
        elif not is_valid_name(response):
            print(f"Invalid {label.lower()} name. Use {ALLOWED_NAME_CHARACTERS} only.")
            pass
        else:
            return response
    
    print(f"Too many invalid attempts.\n\
          Using default name '{default_name}'.")
    sleep(1)
    return default_name

def get_build_and_proton_dir(default_build_name: str, default_dir_name: str) -> Tuple[str, str]:
    """Prompt for both custom names before the build starts, with defaults as fallbacks."""
    build_name = get_name("Please enter the build name: ", default_build_name, "Build")
    proton_dir = get_proton_dir(default_dir_name)
    return build_name, proton_dir

def move_proton_dir(home_dir: str, proton_dir: str, proton_dir_exists: bool) -> None:
    compatibilitytools_dir = os.path.join(home_dir, ".steam", "root", "compatibilitytools.d")
    target_dir = os.path.join(compatibilitytools_dir, proton_dir)
    staged_dir = f"{target_dir}.tmp"

    if os.path.exists(staged_dir):
        subprocess.run(["rm", "-rf", staged_dir], check=True)
    subprocess.run(["cp", "-r", "redist", staged_dir], check=True)
    if proton_dir_exists:
        subprocess.run(["rm", "-rf", target_dir], check=True)
    subprocess.run(["mv", staged_dir, target_dir], check=True)
    print(f"Proton has been moved to your Steam compatibilitytools.d directory as {proton_dir}.")

# -- Main function --

def main() -> None:
    # Variables
    _GIT_REPO: str = "https://github.com/ValveSoftware/Proton.git"
    _GIT_BRANCH: str = "bleeding-edge"
    _BUILD_NAME: str = "my_build"
    _PROTON_DIR: str = "proton-bleeding-edge"
    _HOME_DIR: str = os.path.expanduser("~")

    # Check if the Proton directory already exists
    if os.path.exists("Proton"):
        # If it exists, just update the repository and submodules
        update_existing_proton_repo()
    else:
        # Clone the Proton repository and checkout the bleeding-edge branch
        print("Cloning the Proton repository...")
        subprocess.run(["git", "clone", "-b", _GIT_BRANCH, "--recurse-submodules", _GIT_REPO], check=True)
        os.chdir("Proton")
        print("Repo has been cloned successfully.")

    sleep(2)

    build_name, proton_dir = user_query(
        input_message = "Would you like to give Proton custom build and directory names? [Y/n] ",
        case_y = lambda: get_build_and_proton_dir(_BUILD_NAME, _PROTON_DIR),
        case_n = lambda: (_BUILD_NAME, _PROTON_DIR),
        case_empty = lambda: get_build_and_proton_dir(_BUILD_NAME, _PROTON_DIR),
        case_ = lambda: RETRY,
        max_attempts = MAX_NAME_ATTEMPTS,
        fallback_message = f"Too many invalid attempts.\nUsing default names '{_BUILD_NAME}' and '{_PROTON_DIR}'.",
        fallback_script = lambda: (_BUILD_NAME, _PROTON_DIR)
        )

    # Build Proton
    os.makedirs("build", exist_ok=True)
    os.chdir("build")
    subprocess.run(["../configure.sh", "--enable-ccache", f"--build-name={build_name}"], check=True)

    _JOBS = os.cpu_count() or 1
    print(f"Creating Jobs: {_JOBS} created")
    subprocess.run(["make", f"-j{_JOBS}", "redist"], check=True)

    print("Proton has finished compiling.")

    proton_dir_exists = os.path.exists(f"{_HOME_DIR}/.steam/root/compatibilitytools.d/{proton_dir}")

    if proton_dir_exists:
        user_query(
            input_message = f"The directory {proton_dir} already exists in Steam compatibilitytools.d. Would you like to overwrite it? [Y/n] ",
            case_y = lambda: move_proton_dir(_HOME_DIR, proton_dir, proton_dir_exists),
            case_empty = lambda: move_proton_dir(_HOME_DIR, proton_dir, proton_dir_exists),
            max_attempts = MAX_NAME_ATTEMPTS
            )
    else:
        user_query(
            input_message = "Would you like this script to move the build to your Steam compatibilitytools.d directory? [Y/n] ",
            case_y = lambda: move_proton_dir(_HOME_DIR, proton_dir, proton_dir_exists),
            case_empty = lambda: move_proton_dir(_HOME_DIR, proton_dir, proton_dir_exists),
            max_attempts = MAX_NAME_ATTEMPTS
            )

if __name__ == "__main__":
    main()
    print("Program will now close.")
