import os
import subprocess
from time import sleep

GIT_REPO = "https://github.com/ValveSoftware/Proton.git"
GIT_BRANCH = "bleeding-edge"

# Check if the Proton directory already exists
if os.path.exists("Proton"):
    # If it exists, just update the repository and submodules
    print("Proton directory already exists. Updating the repository and submodules...")
    os.chdir("Proton")
    subprocess.run(["git", "pull", "--recurse-submodules"])
else:
    # Clone the Proton repository and checkout the bleeding-edge branch
    print("Cloning the Proton repository...")
    subprocess.run(["git", "clone", "-b", "bleeding-edge", "--recurse-submodules", GIT_REPO])
    os.chdir("Proton")
    print("Repo has been cloned successfully.")
    sleep(2)

# Build Proton
subprocess.run(["mkdir", "build"])
os.chdir("build")
subprocess.run(["../configure.sh", "--enable-ccache", "--build-name=my_build"])
subprocess.run(["make", "redist"])

print("Proton has finished compiling.")

proton_folder = "proton-bleeding-edge"
user_response = input("Would you like to give Proton a custom folder name? Type Y or N. ")
while user_response != 'N':
    if user_response == "y":
        proton_folder = input("Please enter the folder name: ")
        break
    if user_response == "n":
        break
    else:
        print("Please type Y or N.")
        user_response = input().lower()

user_response = input("Would you like this script to move the file over to your Steam compatibilitytools.d folder? Type Y or N to continue. ").lower()
while user_response != 'N':
    if user_response == "y":
        home_directory = os.path.expanduser("~")
        subprocess.run(["cp", "-r", "dist", f"{home_directory}/.steam/root/compatibilitytools.d/{proton_folder}"])
        print(f"Proton has been moved to your Steam compatibilitytools.d folder as {proton_folder}.")
        break
    if user_response == "n":
        print("Program will now close.")
        exit(0)
    else:
        print("Please type Y or N.")
        user_response = input().lower()
