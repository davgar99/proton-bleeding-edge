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
subprocess.run(["mkdir", "-p", "build"])
os.chdir("build")
subprocess.run(["../configure.sh", "--enable-ccache", "--build-name=my_build"])
subprocess.run(["make", "redist"])
print("Proton has finished compiling.")

# Ask the user if they want to give Proton a custom folder name
proton_folder = "proton-bleeding-edge"
user_response = input("Would you like to give Proton a custom folder name? [Y/n] ").lower().strip()
while user_response not in ['y', 'n', '']:
    user_response = input("Please type Y or N. ").lower().strip()
if user_response == 'y' or user_response == '':
    proton_folder = input("Please enter the folder name: ")
    print(f"Folder name will be: {proton_folder}")
elif user_response == 'n':
    print(f"Folder will use default name: {proton_folder}")

# Ask the user if they want to move the file over to their Steam compatibilitytools.d folder
user_response = input("Would you like to move the file over to your Steam compatibilitytools.d folder? [Y/n] ").lower().strip()
while user_response not in ['y', 'n', '']:
    user_response = input("Please type Y or N. ").lower().strip()
if user_response == 'y' or user_response == '':
    home_directory = os.path.expanduser("~")
    # Check if the Steam compatibilitytools.d folder exists, if not create it
    if not os.path.exists(f"{home_directory}/.steam/root/compatibilitytools.d"):
        os.makedirs(f"{home_directory}/.steam/root/compatibilitytools.d")
    # Check if the Proton folder already exists in the Steam compatibilitytools.d folder, if so, ask the user if they want to overwrite it
    if os.path.exists(f"{home_directory}/.steam/root/compatibilitytools.d/{proton_folder}"):
        user_response = input(f"The folder {proton_folder} already exists in your Steam compatibilitytools.d folder. Would you like to overwrite it? [Y/n] ").lower().strip()
        while user_response not in ['y', 'n', '']:
            user_response = input("Please type Y or N. ").lower().strip()
        if user_response == 'y' or user_response == '':
            subprocess.run(["rm", "-rf", f"{home_directory}/.steam/root/compatibilitytools.d/{proton_folder}"])
            print(f"Folder {proton_folder} has been removed from your Steam compatibilitytools.d folder.")
        elif user_response == 'n':
            print("Program will now close.")
            exit(0)
    subprocess.run(["cp", "-r", "dist", f"{home_directory}/.steam/root/compatibilitytools.d/{proton_folder}"])
    print(f"Proton has been moved to your Steam compatibilitytools.d folder as {proton_folder}.")
elif user_response == 'n':
    print("Program will now close.")
    exit(0)
