import os
import json
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN_PR_REVIEW")
# Define the transport with the endpoint URL
transport = AIOHTTPTransport(
    url='https://api.github.com/graphql',
    headers={'Authorization': f'Bearer {GITHUB_TOKEN}'},
)
client = Client(transport=transport, fetch_schema_from_transport=True)

# get_repos takes a string and
# returns a list of repositories
def get_repos_gql(org: str) -> list[str]:
    print(f"Getting repos for {org}")
    # Define the GraphQL query
    query = gql(f'''
    {{
      organization(login: "{org}") {{
        repositories(first: 10) {{
          nodes {{
            name
            url
          }}
        }}
      }}
    }}
    ''')
    response = client.execute(query)
    pretty_json = json.dumps(response, indent=4)
    print(pretty_json)
    return ["repo1", "repo2", "repo3"]
