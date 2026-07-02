import os
import subprocess

GIT_REPO = "https://github.com/ValveSoftware/Proton.git"
GIT_BRANCH = "bleeding-edge"

subprocess.run(["git", "clone", "-b", "bleeding-edge", "--recurse-submodules", GIT_REPO])
print("Cloning complete.")

os.chdir("Proton")
subprocess.run(["pwd"])

subprocess.run(["mkdir", "build"])
os.chdir("build")
subprocess.run(["../configure.sh", "--enable-ccache", "--build-name=my_build"])

subprocess.run(["make", "redist"])

print('Proton has been compiled. You can find the files under "Proton/build/dist"')
