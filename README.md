# python-sanity

Python client for [Sanity.io](https://sanity.io) CMS HTTP API.

> **ℹ️ Note:**
> This package is an active **fork** of the original project at [OmniPro-Group/sanity-python](https://github.com/OmniPro-Group/sanity-python/).

## Install

Available on pypi as package `python-sanity`

Install with `uv`:

```sh
uv add python-sanity
```

Install with `pip`:

```sh
pip install python-sanity
```

## Environment Variables

You can pass parameters to the client constructor directly, but it is recommended to use environment variables.

| Variable | Description | Required | Default Value |
|----------|-------------|----------|--------------|
| SANITY_PROJECT_ID | The project ID | Yes | |
| SANITY_DATASET | The dataset to use | No | `production` |
| SANITY_API_TOKEN | The API token | Yes | |
| SANITY_LOG_LEVEL | Level of logging | No | `INFO` |

## Examples

```python
from sanity.client import Client
import logging
from scripts.colour_json import print_json_in_colour

logger = logging.getLogger(__name__)

project_id = "<project id>"
dataset = "<dataset>"
token = "<api token>"

client = Client(
    logger,
    project_id=project_id,
    dataset=dataset,
    token=token,
    use_cdn=True
)

# GET Query Method
result = client.query(
    groq="count(*[_type == 'post'])",
    explain=False,
    variables={
        "language": "es",
        "t": 4
    },
    method="GET"
)
print_json_in_colour(result)

# POST Query Method
result = client.query(
    groq="count(*[_type == 'post'])",
    variables={
        "language": "es",
        "t": 4
    },
    method="POST"
)
print_json_in_colour(result)

# Assets
png = "https://some.web.address.com/some_name.png"
result = client.assets(file_path=png)
print_json_in_colour(result)

png2 = "some_file_path/name"
result = client.assets(file_path=png2, mime_type="image/png")
print_json_in_colour(result)

# Mutate
transactions = [
    {
        "createOrReplace": {
            "_id": "speaker.asdf",
            "_type": "speaker",
            "title": "Some Name",
            "slug": {
                "_type": "slug",
                "current": "some-name"
            },
            'image': {
              '_type': 'image',
              'asset': {
                '_ref': 'image-6ffb37d2eeabc7d07b3ca485c7b497e77bdcccd4-1232x1280-png',
                '_type': 'reference'
              }
            }
        }
    }
]
result = client.mutate(
    transactions=transactions,
    return_ids=False,
    return_documents=False,
    visibility="sync",
    dry_run=False,
)
print_json_in_colour(result)
```
