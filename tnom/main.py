from pathlib import Path
import argparse
from set_up_db import init_and_check_db
import config_load
from check_apis import check_apis
async def main():
    # Define args
    working_dir: Path = Path.cwd()
    config_path: Path = working_dir / "config.yml"
    alert_path: Path = working_dir / "alert.yml"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--working_dir",
        type=str,
        help="""The working directory where the config and alert YAML
        files are located and where the database is initialized and checked.

        Example: --working_dir /home/user/tnom""",
        default=working_dir,
        required=False,
    )
    parser.add_argument(
        "--config_path",
        type=str,
        help="""The path to the config YAML file

        Example: --config_path /home/user/tnom/config.yml""",
        default=config_path,
        required=False,
    )
    parser.add_argument(
        "--alert_path",
        type=str,
        help="""The path to the alert YAML file

        Example: --alert_path /home/user/tnom/alert.yml""",
        required=False,
        default=alert_path,
    )
    args = parser.parse_args()
    if args.working_dir:
        working_dir = Path(args.working_dir)

    # Step one - Initialize and check the database
    init_and_check_db(working_dir)

    # Step two - Load the config and alert YAML files
    config_yml = config_load.load_config_yml(args.config_path)
    alert_yml = config_load.load_alert_yml(args.alert_path)

    # Step three - check APIs
    # Should repeat from here
    healthy_apis = await check_apis(config_yml)

    # Step four - Make query with random healthy API
    