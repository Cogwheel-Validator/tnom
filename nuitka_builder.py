"""Nutkia Builder script."""
import subprocess
from pathlib import Path


def run_nuitka_build() -> None:
    # Get the poetry virtual environment path
    """Build the tnom executable with Nuitka.

    This function builds the tnom executable by:
    1. Getting the poetry virtual environment path
    2. Getting the project root directory
    3. Creating the build command for Nuitka
    4. Running the build command

    Args:
        None

    Returns:
        None

    Raises:
        subprocess.CalledProcessError: If the build command fails

    """
    result = subprocess.run(["poetry", "env", "info", "--path"],
                          capture_output=True, text=True, check=False)
    venv_path = result.stdout.strip()

    # Get the project root directory
    project_root = Path(__file__).parent

    # Build command for Nuitka (removed numpy plugin and --follow-imports)
    build_command = [
        "python", "-m", "nuitka",
        "--enable-plugin=anti-bloat",
        "--include-package=tnom",
        "--include-package=alerts",
        "--include-package=config_load",
        "--include-package=database_handler",
        "--include-package=dead_man_switch",
        "--include-package=query",
        "--include-package=utility",
        "--include-data-dir={}=.".format(project_root / "tnom"),
        "--standalone",
        "--output-dir=build",
        "--output-filename=tnom",
        str(project_root / "tnom" / "main.py"),
    ]

    # Run the build command
    subprocess.run(build_command, check=False)

if __name__ == "__main__":
    run_nuitka_build()
