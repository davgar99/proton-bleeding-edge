import os
import re
import subprocess
from time import sleep
from typing import Callable

# -- Global Variables --

RETRY = object()

# -- Helper functions --

def none():
    return None

def user_query(
        input_message: str,
        case_y: Callable[[], object] = lambda: none(), 
        case_n: Callable[[], object] = lambda: none(),
        case_empty: Callable[[], object] = lambda: none(),
        case_: Callable[[], object] = lambda: RETRY,
        max_attempts: int = 1,
        fail_message: str = "Invalid input, try again.",
        fallback_message: str = "Too many invalid attempts.",
        fallback_script: Callable[[], object] = lambda: none()
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

def is_valid_dir_name(dir_name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]+", dir_name))

# -- Primary functions --

def get_proton_dir(default_dir_name: str) -> str:
    return get_name("Please enter the directory name: ", default_dir_name, "Directory")

def get_name(input_message: str, default_name: str, label: str) -> str:
    attempt: int = 1
    while attempt <= 3:
        attempt += 1
        response = input(input_message).strip()
        if not response:
            print(f"{label} name cannot be empty.")
            pass
        elif not is_valid_dir_name(response):
            print(f"Invalid {label.lower()} name. Use letters, digits, '.', '_' and '-' only.")
            pass
        else:
            return response
    
    print(f"Too many invalid attempts.\n\
          Using default name '{default_name}'.")
    sleep(1)
    return default_name

def get_build_and_proton_dir(default_build_name: str, default_dir_name: str) -> tuple[str, str]:
    build_name = get_name("Please enter the build name: ", default_build_name, "Build")
    proton_dir = get_proton_dir(default_dir_name)
    return build_name, proton_dir

def move_proton_dir(home_dir: str, proton_dir: str, proton_dir_exists: bool) -> None:
    if proton_dir_exists:
        subprocess.run(["rm", "-rf", f"{home_dir}/.steam/root/compatibilitytools.d/{proton_dir}"], check=True)
    subprocess.run(["cp", "-r", "dist", f"{home_dir}/.steam/root/compatibilitytools.d/{proton_dir}"], check=True)
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
        print("Proton directory already exists. Fetching remote repository:")
        os.chdir("Proton")

        # Fetch remote repository
        subprocess.run(["git", "fetch", "--recurse-submodules"], check=True)
        local = subprocess.check_output(["git", "rev-parse", "@"]).strip()
        remote = subprocess.check_output(["git", "rev-parse", "@"]).strip()

        if local != remote:
            print("Updating your local repository...")
            subprocess.run(["git", "pull", "--recurse-submodules"], check=True)
        else:
            print("Your local repository is on the latest version already.")
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
        max_attempts = 3,
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
            max_attempts = 3
            )
    else:
        user_query(
            input_message = "Would you like this script to move the build to your Steam compatibilitytools.d directory? [Y/n] ",
            case_y = lambda: move_proton_dir(_HOME_DIR, proton_dir, proton_dir_exists),
            case_empty = lambda: move_proton_dir(_HOME_DIR, proton_dir, proton_dir_exists),
            max_attempts = 3
            )

if __name__ == "__main__":
    main()
    print("Program will now close.")
