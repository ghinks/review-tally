# import argparse and create a function to parse command line arguments
# and return the parsed arguments, which will be used by the main function
# to get the start and end dates for the pull requests and the organization name

import argparse
from datetime import datetime, timedelta


def parse_cmd_line() -> [str, datetime, datetime, str]:
    """Parse command line arguments

    :return:
    organization name, start date, end date, language
    """
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
    parser.add_argument("-o", "--org", required=True, help=org_help)
    date_format = "%Y-%m-%d"
    two_weeks_ago = datetime.now() - timedelta(days=14)
    today = datetime.now()
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
    parser.add_argument("-l", "--language", required=False, help=language_selection)
    args = parser.parse_args()
    # catch ValueError if the date format is not correct
    try:
        if args.start_date:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        if args.end_date:
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError as e:
        print("Error:", e)
        exit(1)
    return args.org, start_date, end_date, args.language
