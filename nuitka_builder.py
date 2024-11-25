"""Nutkia Builder script."""
import logging
import subprocess
import sys
from pathlib import Path


def run_nuitka_build() -> None:
    """Builds the project using Nuitka.

    This function constructs a build command to compile the project
    with Nuitka, including specific packages and plugins. It executes
    the command using the current Python interpreter, aiming to
    produce a standalone executable in the "build" directory.

    The build command includes:
        - Anti-bloat plugin
        - Specified packages (tnom, alerts, config_load, database_handler,
          dead_man_switch, query, utility)
        - Inclusion of the 'tnom' data directory

    If the build succeeds, a success message is logging.infoed and the
    executable is stored in the "build" directory. If the build
    fails, an error message is logging.infoed and the script exits with a
    non-zero status.
    """
    project_root = Path(__file__).parent

    # Build command for Nuitka
    build_command = [
        sys.executable,  # Use the current Python interpreter
        "-m",
        "nuitka",
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
    try:
        subprocess.run(build_command, check=True)  # noqa: S603
        logging.info("\nBuild completed successfully!")
        logging.info("The executable can be found in the 'build' directory")
    except subprocess.CalledProcessError as e:
        logging.exception("\nBuild failed with error: %s", e)  # noqa: TRY401
        sys.exit(1)
    except Exception as e:
        logging.exception("\nAn unexpected error occurred: %s", e)  # noqa: TRY401
        sys.exit(1)

if __name__ == "__main__":
    run_nuitka_build()
