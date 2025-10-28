# python-sanity

<svg width="452" height="160" viewBox="0 0 452 160" fill="none" xmlns="http://www.w3.org/2000/svg">
<g clip-path="url(#clip0_2001_20)">
<path d="M46.6255 54.491C34.7181 45.5113 22.6571 38.5467 22.6571 28.4122C22.6571 22.3314 28.032 16.0975 35.4387 16.0975C48.799 16.0975 56.6428 30.0031 64.3448 47.3968H69.1408V7.40063H35.734C8.13908 7.40063 0 24.0637 0 37.109C0 54.2082 14.0928 64.3545 30.0638 76.2332C41.2506 84.494 50.6891 92.1774 50.6891 101.016C50.6891 110.585 44.1566 116.088 35.8757 116.088C27.0161 116.088 13.9392 104.492 4.79603 80.4402H0V124.785H38.2029C61.7341 124.785 73.4998 106.236 73.9368 91.3054C74.5157 73.9117 59.5606 64.2131 46.6255 54.5028V54.491Z" fill="#0B0B0B"/>
<path d="M150.626 111.009V64.2014C150.626 43.9087 137.986 38.5586 119.688 38.5586H87.1555L87.2972 71.602H92.6721C98.3423 57.5432 106.47 47.2555 115.187 47.2555C122.736 47.2555 126.079 53.7722 126.079 60.5836V66.9589C113.876 74.2063 81.3435 80.2871 81.3435 102.312C81.3435 115.063 90.2032 125.645 103.127 125.645C114.313 125.645 122.015 118.398 125.937 109.854C126.658 116.96 131.312 124.785 141.92 124.785H158.623V118.41C153.249 118.41 150.638 114.792 150.638 111.021L150.626 111.009ZM125.642 103.762C123.315 107.097 119.688 110.868 115.329 110.868C109.234 110.868 105.312 106.236 105.312 96.962C105.312 86.3796 119.546 79.5682 125.654 74.5009V103.773L125.642 103.762Z" fill="#0B0B0B"/>
<path d="M280.627 29.567C289.924 29.567 295.736 23.0502 295.736 14.6362C295.736 6.22216 289.924 0 280.627 0C271.33 0 265.377 6.23394 265.377 14.6362C265.377 23.0385 271.626 29.567 280.627 29.567Z" fill="#0B0B0B"/>
<path d="M425.016 38.5467V44.9221C434.171 44.9221 436.782 49.7065 432.281 62.5986L421.389 92.0124L407.45 56.2233C404.249 49.2705 405.997 44.9221 412.683 44.9221V38.5467H343.401V9.56891H336.868C334.978 19.4207 324.665 38.5467 307.088 38.5467V44.9221H318.416V104.48C318.416 114.473 321.759 125.786 341.227 125.786H371.444V93.0377H366.07C363.896 100.721 359.384 116.076 349.65 116.076C344.275 116.076 343.401 110.137 343.401 105.352V47.6796H371.149C374.492 47.6796 377.977 48.1156 379.714 52.1694L409.198 124.914C403.528 137.807 393.806 139.845 376.37 134.483V159.985C380.871 159.985 392.495 160.126 394.527 159.549C405.997 156.214 413.841 133.753 417.042 125.056L442.026 57.6727C444.791 50.2839 447.106 44.9221 451.902 44.9221V38.5467H425.028H425.016Z" fill="#0B0B0B"/>
<path d="M246.925 111.009V61.5969C246.925 46.0887 239.518 36.8144 224.846 36.8144C211.923 36.8144 204.434 45.7587 198.705 54.0785V38.5585H165.581V44.9338C171.251 44.9338 173.72 48.4102 173.72 52.464V111.009C173.72 114.921 170.814 118.398 165.581 118.398V124.773H206.832V118.398C201.599 118.398 198.693 114.921 198.693 111.009V61.9858C202.036 57.5431 205.899 52.7587 212.348 52.7587C218.444 52.7587 221.94 57.6845 221.94 63.6239V111.009C221.94 114.921 219.035 118.398 213.801 118.398V124.773H255.052V118.398C249.819 118.398 246.913 114.921 246.913 111.009H246.925Z" fill="#0B0B0B"/>
<path d="M295.157 111.009V38.5586H262.033V44.9339C267.704 44.9339 270.173 48.4103 270.173 52.4642V111.009C270.173 114.921 267.267 118.398 262.033 118.398V124.773H303.284V118.398C298.051 118.398 295.145 114.921 295.145 111.009H295.157Z" fill="#0B0B0B"/>
</g>
<defs>
<clipPath id="clip0_2001_20">
<rect width="452" height="160" fill="white"/>
</clipPath>
</defs>
</svg>


Python client for [Sanity.io](https://sanity.io) CMS HTTP API. Sanity is a hosted CMS solution for content management. This project is not affiliated with Sanity.io and is a third-party package.

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
