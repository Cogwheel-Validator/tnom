"""build.py - Script to create executable using Poetry and PyInstaller"""

import argparse
import os
import shutil
import subprocess

import PyInstaller.__main__


def clean_build():
    """Clean build artifacts."""
    dirs_to_clean = ["build", "dist", "__pycache__"]
    files_to_clean = ["*.spec"]

    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Cleaned {dir_name}/")

    import glob

    for spec_file in glob.glob("*.spec"):
        os.remove(spec_file)
        print(f"Cleaned {spec_file}")


def test_executable():
    """Test the built executable."""
    print("Testing executable...")

    tests = [
        ["./dist/tnom", "--version"],
    ]

    for test_cmd in tests:
        try:
            result = subprocess.run(
                test_cmd, capture_output=True, text=True, check=True
            )
            print(f"✓ Test passed: {' '.join(test_cmd)}")
            print(f"  Output: {result.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Test failed: {' '.join(test_cmd)}")
            print(f"  Error: {e.stderr.strip()}")
            return False
    return True


def build_executable(clean=False, test=False):
    """Build the executable."""
    if clean:
        clean_build()

    pyinstaller_args = [
        "tnom/main.py",
        "--onefile",
        "--name=tnom",
        # Module imports
        "--hidden-import=alerts",
        "--hidden-import=config_load",
        "--hidden-import=database_handler",
        "--hidden-import=dead_man_switch",
        "--hidden-import=query",
        "--hidden-import=utility",
        # External packages
        "--hidden-import=yaml",
        "--hidden-import=aiohttp",
        "--hidden-import=sqlite3",
        "--hidden-import=pdpyras",
        "--hidden-import=telegram",
    ]

    PyInstaller.__main__.run(pyinstaller_args)

    if test:
        if not test_executable():
            print("Build verification failed!")
            exit(1)
        print("All tests passed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build script for tnom executable")
    parser.add_argument(
        "--clean", action="store_true", help="Clean build artifacts before building"
    )
    parser.add_argument(
        "--test", action="store_true", help="Test the executable after building"
    )
    args = parser.parse_args()

    build_executable(clean=args.clean, test=args.test)
