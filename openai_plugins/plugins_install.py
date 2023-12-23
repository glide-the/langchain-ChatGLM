import os
import subprocess


def run_install_script(module_path, install_file):
    install_script_path = os.path.join(module_path,install_file)
    if os.path.exists(install_script_path):
        subprocess.run(["python", install_script_path])


