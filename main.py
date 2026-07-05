import os
import subprocess
from time import sleep

GIT_REPO = "https://github.com/ValveSoftware/Proton.git"
GIT_BRANCH = "bleeding-edge"

subprocess.run(["git", "clone", "-b", "bleeding-edge", "--recurse-submodules", GIT_REPO])
print("Repo has been cloned successfully.")
sleep(2)

os.chdir("Proton")
subprocess.run(["pwd"])

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

home_directory = os.path.expanduser("~")

user_response = input("Would you like this script to move the file over to your Steam compatibilitytools.d folder? Type Y or N to continue. ").lower()
while user_response != 'N':
    if user_response == "y":
        subprocess.run(["cp", "-v", "Proton/build/dist", f"{home_directory}/.steam/root/compatibilitytools.d/{proton_folder}"])
        break
    if user_response == "n":
        print("Program will now close.")
        exit(0)
    else:
        print("Please type Y or N.")
        user_response = input().lower()
