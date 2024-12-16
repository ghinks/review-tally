from .queries.get_prs import get_pull_requests_between_dates

from .queries.get_repos_gql import get_repos_by_language
from pr_reviews.queries.local_exceptions import GitHubTokenNotDefinedError
from .queries.get_reviewers_rest import get_reviewers_for_pull_requests
from tabulate import tabulate
from .cli.parse_cmd_line import parse_cmd_line
import time

def timestamped_print(message):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}", flush=True)

BATCH_SIZE = 5

def main():
    # map containing the reviewer name and the number of pull requests reviewed
    start_time = time.time()
    timestamped_print("Starting process")
    reviewer_prs = {}
    org_name, start_date, end_date, language = parse_cmd_line()
    try:
        timestamped_print(f"Calling get_repos_by_language {time.time() - start_time:.2f} seconds")
        repositories = get_repos_by_language(org_name, language)
    except GitHubTokenNotDefinedError as e:
        print("Error:", e)
        return
    timestamped_print(f"Finished get_repos_by_language {time.time() - start_time:.2f} seconds for {len(repositories)} repositories")
    timestamped_print(f"Calling get_pull_requests_between_dates {time.time() - start_time:.2f} seconds")
    # it is possible to take these asynchronous requests and
    # batch them to improve performance.
    # get all the repo names
    repo_names = [repo["name"] for repo in repositories]
    print(repo_names)
    for repo in repo_names:
         timestamped_print(f"Processing {repo}")
         pull_requests = get_pull_requests_between_dates(
             org_name, repo, start_date, end_date
         )
         timestamped_print(f"Finished get_pull_requests_between_dates {time.time() - start_time:.2f} seconds for {len(pull_requests)} pull requests")
         pr_numbers = [pr["number"] for pr in pull_requests]
         # create batches of 5 pr_numbers
         pr_numbers_batched = [pr_numbers[i:i + BATCH_SIZE] for i in range(0, len(pr_numbers), 5)]
         for pr_numbers in pr_numbers_batched:
            reviewers = get_reviewers_for_pull_requests(
                org_name, repo, pr_numbers
            )
            for reviewer in reviewers:
                if "login" not in reviewer:
                    raise ValueError("login not found in reviewer")
                if reviewer["login"] in reviewer_prs:
                    reviewer_prs[reviewer["login"]] += 1
                else:
                    reviewer_prs[reviewer["login"]] = 1
         timestamped_print(f"Finished processing {repo} {time.time() - start_time:.2f} seconds")
    # convert the dictionary to a list of lists and print out with tabulate
    timestamped_print(f"Printing results {time.time() - start_time:.2f} seconds")
    table = [[k, v] for k, v in reviewer_prs.items()]
    # convert the dictionary to a list of lists and sort by the number of PRs reviewed
    table = sorted(table, key=lambda x: x[1], reverse=True)
    print(tabulate(table))


if __name__ == "__main__":
    main()
