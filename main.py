import os
import re
import shutil
import subprocess
import tempfile
from time import sleep
from typing import Any, Callable
from urllib.parse import urlparse

# -- Global Variables --

RETRY = object()

# -- Helper functions --

def none():
    return None

def user_query(
        input_message: str,
        case_y: Callable[[], Any] = lambda: none(),
        case_n: Callable[[], Any] = lambda: none(),
        case_empty: Callable[[], Any] = lambda: none(),
        case_: Callable[[], Any] = lambda: RETRY,
        max_attempts: int = 1,
        fail_message: str = "Invalid input, try again.",
        fallback_message: str = "Too many invalid attempts.",
        fallback_script: Callable[[], Any] = lambda: none()
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
    return dir_name not in {".", ".."} and bool(re.fullmatch(r"[A-Za-z0-9._-]+", dir_name))

def canonical_git_remote(url: str) -> str:
    """Normalize common Git remote URL forms for repository identity checks."""
    value = url.strip().rstrip("/")
    scp_style = re.fullmatch(r"git@([^:]+):(.+)", value)
    if scp_style:
        host, path = scp_style.groups()
    else:
        parsed = urlparse(value)
        if not parsed.hostname:
            return value.removesuffix(".git")
        host = parsed.hostname
        path = parsed.path.lstrip("/")

    return f"{host.lower()}/{path.removesuffix('.git')}"

def prepare_proton_repository(repo_url: str, branch: str) -> None:
    proton_path = "Proton"
    if os.path.lexists(proton_path):
        if os.path.islink(proton_path) or not os.path.isdir(proton_path):
            raise RuntimeError("Existing Proton path must be a real directory, not a file or symlink.")

        try:
            inside_worktree = subprocess.check_output(
                ["git", "-C", proton_path, "rev-parse", "--is-inside-work-tree"],
                text=True,
            ).strip()
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("Existing Proton directory is not a usable Git checkout.") from exc
        if inside_worktree != "true":
            raise RuntimeError("Existing Proton directory is not a usable Git checkout.")

        dirty = subprocess.check_output(
            ["git", "-C", proton_path, "status", "--porcelain"],
            text=True,
        ).strip()
        if dirty:
            raise RuntimeError("Existing Proton checkout has uncommitted changes; commit or stash them before building.")

        current_branch = subprocess.check_output(
            ["git", "-C", proton_path, "branch", "--show-current"],
            text=True,
        ).strip()
        if current_branch != branch:
            raise RuntimeError(
                f"Existing Proton checkout is on branch '{current_branch or '(detached HEAD)'}', expected '{branch}'."
            )

        origin_url = subprocess.check_output(
            ["git", "-C", proton_path, "remote", "get-url", "origin"],
            text=True,
        ).strip()
        if canonical_git_remote(origin_url) != canonical_git_remote(repo_url):
            raise RuntimeError(
                f"Existing Proton checkout origin '{origin_url}' does not match the expected repository '{repo_url}'."
            )

        print("Proton directory already exists. Fetching remote repository:")
        subprocess.run(
            ["git", "-C", proton_path, "fetch", "origin", branch, "--recurse-submodules"],
            check=True,
        )
        local = subprocess.check_output(["git", "-C", proton_path, "rev-parse", "HEAD"], text=True).strip()
        remote = subprocess.check_output(["git", "-C", proton_path, "rev-parse", "FETCH_HEAD"], text=True).strip()

        ancestry = subprocess.run(
            ["git", "-C", proton_path, "merge-base", "--is-ancestor", local, remote],
            check=False,
        )
        if ancestry.returncode != 0:
            raise RuntimeError(
                f"Existing Proton checkout has commits not present on origin/{branch}; refusing to overwrite divergent history."
            )

        if local != remote:
            print("Updating your local repository...")
            subprocess.run(["git", "-C", proton_path, "merge", "--ff-only", "FETCH_HEAD"], check=True)
        else:
            print("Your local repository is on the latest version already.")

        # Fetching submodules does not update their checked-out commits. Keep
        # the working tree aligned with the exact superproject revision before
        # configure/build so stale submodules cannot produce a mixed build.
        subprocess.run(
            ["git", "-C", proton_path, "submodule", "update", "--init", "--recursive"],
            check=True,
        )
    else:
        print("Cloning the Proton repository...")
        subprocess.run(
            ["git", "clone", "-b", branch, "--recurse-submodules", repo_url, proton_path],
            check=True,
        )
        print("Repo has been cloned successfully.")

    os.chdir(proton_path)

# -- Primary functions --

def get_proton_dir(default_dir_name: str) -> str:
    attempt: int = 1
    while attempt <= 3:
        attempt += 1
        response = input("Please enter the directory name: ").strip()
        if not response:
            print("Directory name cannot be empty.")
            pass
        elif not is_valid_dir_name(response):
            print("Invalid directory name. Use letters, digits, '.', '_' '-' only; '.' and '..' are not allowed.")
            pass
        else:
            return response

    print(f"Too many invalid attempts.\nUsing default name '{default_dir_name}'.")
    sleep(1)
    return(default_dir_name)

def move_proton_dir(home_dir: str, proton_dir: str) -> None:
    if not is_valid_dir_name(proton_dir):
        raise ValueError("Invalid Proton directory name")

    compatibility_tools_dir = os.path.realpath(
        os.path.join(home_dir, ".steam", "root", "compatibilitytools.d")
    )
    target_dir = os.path.join(compatibility_tools_dir, proton_dir)

    # Never follow or relocate a caller-selected final-component symlink. This
    # check intentionally happens before any backup, rename, or removal work.
    if os.path.lexists(target_dir) and os.path.islink(target_dir):
        raise ValueError("Refusing to overwrite a symlink in compatibilitytools.d")

    # Steam does not always create compatibilitytools.d until a custom tool is
    # installed, so make sure the trusted parent exists before staging a copy.
    os.makedirs(compatibility_tools_dir, exist_ok=True)

    # Re-check after creating the parent in case the destination appeared in
    # the meantime. Existing non-directory entries are not safe overwrite targets.
    if os.path.lexists(target_dir) and os.path.islink(target_dir):
        raise ValueError("Refusing to overwrite a symlink in compatibilitytools.d")
    if os.path.lexists(target_dir) and not os.path.isdir(target_dir):
        raise ValueError("Refusing to overwrite a non-directory in compatibilitytools.d")

    temp_dir = tempfile.mkdtemp(prefix=f".{proton_dir}.new-", dir=compatibility_tools_dir)
    backup_dir: str | None = None

    try:
        # Build the complete replacement before touching a working install. If
        # this copy fails (disk full, interruption, permission error), the old
        # Proton directory remains untouched.
        shutil.copytree("dist", temp_dir, dirs_exist_ok=True)

        if os.path.lexists(target_dir):
            if os.path.islink(target_dir):
                raise ValueError("Refusing to overwrite a symlink in compatibilitytools.d")
            if not os.path.isdir(target_dir):
                raise ValueError("Refusing to overwrite a non-directory in compatibilitytools.d")

            # mkdtemp gives us a collision-resistant sibling name. Remove the
            # empty placeholder so the existing directory can be atomically
            # renamed into that path on the same filesystem.
            backup_dir = tempfile.mkdtemp(prefix=f".{proton_dir}.old-", dir=compatibility_tools_dir)
            os.rmdir(backup_dir)
            os.rename(target_dir, backup_dir)

        try:
            # Do not replace anything that appeared unexpectedly after the
            # backup step. This keeps the operation fail-closed under races.
            if os.path.lexists(target_dir):
                raise FileExistsError(f"Install destination appeared during replacement: {target_dir}")
            os.rename(temp_dir, target_dir)
            temp_dir = ""
        except Exception:
            if backup_dir and os.path.lexists(backup_dir) and not os.path.lexists(target_dir):
                os.rename(backup_dir, target_dir)
                backup_dir = None
            raise

        if backup_dir and os.path.lexists(backup_dir):
            try:
                shutil.rmtree(backup_dir)
                backup_dir = None
            except OSError as exc:
                # The new install is already active. Leaving the old backup is
                # safer than treating cleanup failure as a failed installation.
                print(f"Warning: Proton was installed, but old backup cleanup failed: {exc}")

        print(f"Proton has been moved to your Steam compatibilitytools.d directory as {proton_dir}.")
    finally:
        if temp_dir and os.path.lexists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

# -- Main function --

def main() -> None:
    # Variables
    _GIT_REPO: str = "https://github.com/ValveSoftware/Proton.git"
    _GIT_BRANCH: str = "bleeding-edge"
    _PROTON_DIR: str = "proton-bleeding-edge"
    _HOME_DIR: str = os.path.expanduser("~")

    prepare_proton_repository(_GIT_REPO, _GIT_BRANCH)

    sleep(2)

    # Ask for the output name up front, so it can be used both as the Proton
    # build name (what Steam displays) and as the compatibilitytools.d directory name
    proton_dir = user_query(
        input_message = "Would you like to give Proton a custom directory name? [Y/n] ",
        case_y = lambda: get_proton_dir(_PROTON_DIR),
        case_n = lambda: _PROTON_DIR,
        case_empty = lambda: get_proton_dir(_PROTON_DIR),
        case_ = lambda: RETRY,
        max_attempts = 3,
        fallback_message = f"Too many invalid attempts.\nUsing default name '{_PROTON_DIR}'.",
        fallback_script = lambda: _PROTON_DIR
        )

    # Build Proton
    os.makedirs("build", exist_ok=True)
    os.chdir("build")
    subprocess.run(["../configure.sh", "--enable-ccache", f"--build-name={proton_dir}"], check=True)

    _JOBS = os.cpu_count() or 1
    print(f"Creating Jobs: {_JOBS} created")
    subprocess.run(["make", f"-j{_JOBS}", "redist"], check=True)

    print("Proton has finished compiling.")

    proton_dir_exists = os.path.lexists(
        os.path.join(_HOME_DIR, ".steam", "root", "compatibilitytools.d", proton_dir)
    )

    if proton_dir_exists:
        user_query(
            input_message = f"The directory {proton_dir} already exists in Steam compatibilitytools.d. Would you like to overwrite it? [Y/n] ",
            case_y = lambda: move_proton_dir(_HOME_DIR, proton_dir),
            case_empty = lambda: move_proton_dir(_HOME_DIR, proton_dir),
            max_attempts = 3
            )
    else:
        user_query(
            input_message = "Would you like this script to move the file over to your Steam compatibilitytools.d directory? [Y/n] ",
            case_y = lambda: move_proton_dir(_HOME_DIR, proton_dir),
            case_empty = lambda: move_proton_dir(_HOME_DIR, proton_dir),
            max_attempts = 3
            )

if __name__ == "__main__":
    main()
    print("Program will now close.")
