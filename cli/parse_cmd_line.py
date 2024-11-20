# import argparse and create a function to parse command line arguments
# and return the parsed arguments, which will be used by the main function
# to get the start and end dates for the pull requests and the organization name

import argparse
from datetime import datetime


def parse_cmd_line():
    """Parse command line arguments

    :return:
    organization name, start date, end date
    """
    description = """Get pull requests for the organization between dates
    and the reviewers for each pull request. The environment must declare 
    a GTIHUB_TOKEN variable with a valid GitHub token.
    """
    org_help = "Organization name"
    start_date_help = "Start date in the format YYYY-MM-DD"
    end_date_help = "End date in the format YYYY-MM-DD"
    parser = argparse.ArgumentParser(description=description)
    # these arguments are required
    parser.add_argument("-s", "--start_date", required=True, help=start_date_help)
    parser.add_argument("-e", "--end_date", required=True, help=end_date_help)
    parser.add_argument("-o", "--org", required=True, help=org_help)
    args = parser.parse_args()
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    return args.org, start_date, end_date
