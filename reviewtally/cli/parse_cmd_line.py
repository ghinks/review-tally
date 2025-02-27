# import argparse and create a function to parse command line arguments
# and return the parsed arguments, which will be used by the main function
# to get the start and end dates for the pull requests and the organization
# name

import argparse
import importlib.metadata
import sys
from datetime import datetime, timedelta, timezone


def print_toml_version() -> None:
    version = importlib.metadata.version("review-tally")
    print(f"Current version is {version}") # noqa: T201

def parse_cmd_line() -> [str, datetime, datetime, list[str]]:  # type: ignore[valid-type]
    description = """Get pull requests for the organization between dates
    and the reviewers for each pull request. The environment must declare
    a GTIHUB_TOKEN variable with a valid GitHub token.
    """
    org_help = "Organization name"
    start_date_help = "Start date in the format YYYY-MM-DD"
    end_date_help = "End date in the format YYYY-MM-DD"
    language_selection = "Select the language to filter the pull requests"
    parser = argparse.ArgumentParser(description=description)
    # these arguments are required
    parser.add_argument("-o", "--org", required=False,
                        help=org_help)
    date_format = "%Y-%m-%d"
    two_weeks_ago = datetime.now(tz=timezone.utc) - timedelta(days=14)
    today = datetime.now(tz=timezone.utc)
    parser.add_argument(
        "-s",
        "--start_date",
        required=False,
        help=start_date_help,
        default=two_weeks_ago.strftime(date_format),
    )
    parser.add_argument(
        "-e",
        "--end_date",
        required=False,
        help=end_date_help,
        default=today.strftime(date_format),
    )
    # add the language selection argument
    parser.add_argument("-l", "--language", required=False,
                        help=language_selection)
    version_help = """
    Print version and exit
    """
    parser.add_argument("-v", "--version", action="store_true",
                        help=version_help)
    args = parser.parse_args()
    # catch ValueError if the date format is not correct
    try:
        if args.start_date:
            start_date = ((
                datetime.
                    strptime(args.start_date, "%Y-%m-%d")).
                          replace(tzinfo=timezone.utc))
        if args.end_date:
            end_date = ((
                    datetime.
                        strptime(args.end_date, "%Y-%m-%d")).
                           replace(tzinfo=timezone.utc))
    except ValueError as e:
        print("Error:", e) # noqa: T201
        sys.exit(1)
    if args.version:
        print_toml_version()
        sys.exit(0)
    if start_date > end_date:
        print("Error: Start date must be before end date") # noqa: T201
        sys.exit(1)
    # if the language arg has comma separated values, split them
    if args.language is None:
        languages = []
    elif args.language and "," in args.language:
        languages = args.language.split(",")
    else:
        languages = [args.language]
    return args.org, start_date, end_date, languages
