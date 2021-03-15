from typing import List
import requests
from flask import request, g

headers = {"X-Requested-With": "true", "Origin": "https://repl.it"}


main_query = """
query Foo {
  
  team: teamByUsername (username: "5H20202021Pytho") {
    ... on Team {
      members {
        id
        email
        user {
          displayName
          username
        }
      }
      
      templates {
        id
        repl {
          title
        }
        submissions {
          id
          timeSubmitted
          timeLastReviewed
          author {
            id
            username
          }
          repl {
            id
            url
          }
        }
      }
    }
  }
}


"""


def run_graphql_query(query):
    response = requests.post("https://repl.it/graphql", json={"query": query}, headers=headers)
