import logging

from dotenv import load_dotenv

from sanity import Client as SanityClient

load_dotenv()

logger = logging.getLogger("simple_list")

sanity_client = SanityClient(
    logger=logger,
)


def run_example_query():
    response = sanity_client.query(
        groq="*[_type == 'facility']",
        variables={"language": "es", "t": 4},
    )
    print(response)


if __name__ == "__main__":
    run_example_query()
