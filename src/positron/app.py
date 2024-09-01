import os
import json
import yaml
import argparse
import requests
import subprocess
import tarfile
import shutil

# Run the development server
def dev():
    subprocess.run(["env/bin/python3", "-m", "hypercorn", "app:app", "--reload"])

# Build the flatpak package
def build():
    # Check if the manifest file exists
    files = [f for f in os.listdir(".") if f.startswith("manifest.")]
    if not len(files):
        raise Exception("Manifest file not found!")

    # Read the manifest file
    if files[0].endswith(".yml"):
        with open(files[0], "r") as f:
            manifest = yaml.safe_load(f)
    elif files[0].endswith(".json"):
        with open(files[0], "r") as f:
            manifest = json.load(f)
    else:
        raise Exception("Invalid manifest file format!")

    print("Building the flatpak package...")

    # Clean up
    shutil.rmtree(".flatpak-builder", ignore_errors=True)
    shutil.rmtree("build-dir", ignore_errors=True)

    # Get the latest firefox build if it doesn't exist
    if not os.path.exists("firefox.tar.bz2"):
        with requests.get("https://download.mozilla.org/?product=firefox-latest-ssl&os=linux64&lang=en-US", stream=True) as r:
            r.raise_for_status()
            with open("firefox.tar.bz2", "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    # Create wheels if they don't exist
    if not os.path.exists("wheels"):
        subprocess.run(["docker", "build", "-t", "flatpak-wheels", ".", "--no-cache"])
        subprocess.run(["docker", "run", "--name", "flatpak-wheels", "flatpak-wheels"])
        os.makedirs("wheels", exist_ok=True)
        subprocess.run(["docker", "cp", "flatpak-wheels:/app/wheels/.", "wheels"])
        subprocess.run(["docker", "rm", "flatpak-wheels"])

    # Remove old flatpak
    subprocess.run(["flatpak", "uninstall", "-y", manifest["id"]])

    # Build the flatpak
    result = subprocess.run(["flatpak-builder", "--force-clean", "--install", "--user", "build-dir", files[0]], capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception("Flatpak build failed!")

    # Run the flatpak
    subprocess.run(["flatpak", "run", manifest["id"]])

def main():
    parser = argparse.ArgumentParser(description='Build desktop apps with Python')
    parser.add_argument('command', type=str, help='Command to run', choices=['dev', 'build'])
    args = parser.parse_args()

    match args.command:
        case "dev":
            dev()

        case "build":
            build()

if __name__ == "__main__":
    main()