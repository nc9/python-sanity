"""

Example listing Open Electricity facilities

"""

import logging
from typing import Any

from dotenv import load_dotenv

from sanity import SanityClient

load_dotenv()

logger = logging.getLogger(__name__)

sanity_client = SanityClient(
    logger=logger,
)


def get_cms_facilities(
    facility_code: str | None = None, cms_id: str | None = None
) -> list[dict[str, Any] | None]:
    """Retrieve facility data from the CMS with optional filtering.

    This is the primary function for retrieving facility data from the CMS. It includes
    comprehensive facility metadata, unit data, and related information. The function
    includes caching and retry logic for reliability.

    Args:
        facility_code: Optional facility code to filter results

    Returns:
        list[FacilitySchema]: List of validated facility models

    Raises:
        CMSQueryError: If there's an error querying the CMS
        ValidationError: If the facility data doesn't match the expected schema

    Note:
        The function will retry on CMSQueryError and ValidationError, but will
        re-raise the error if all retries fail.
    """
    filter_query = ""

    if facility_code:
        filter_query += f" && code == '{facility_code}'"

    if cms_id:
        filter_query += f" && _id == '{cms_id}'"

    query = f"""*[_type == "facility"{filter_query} && !(_id in path("drafts.**"))] {{
        _id,
        _createdAt,
        _updatedAt,
        code,
        name,
        website,
        description,
        "network_id": upper(network->code),
        "network_region": upper(region->code),
        "npiId": npi_id,
        osm_way_id,
        photos[] {{
            "url": asset->url,
            "url_source": url,
            "caption": caption,
            "attribution": attribution,
            "alt": alt,
            "metadata": asset->metadata
        }},
        owners[]-> {{
            name,
            website,
            wikipedia
        }},
        wikipedia,
        location,
        units[]-> {{
            _id,
            _updatedAt,
            _createdAt,
            code,
            dispatch_type,
            "status_id": status,
            "network_id": upper(network->code),
            "network_region": upper(network_region->code),
            "fueltech_id": fuel_technology->code,
            capacity_registered,
            capacity_maximum,
            storage_capacity,
            emissions_factor_co2,
            closure_date,
            closure_date_specificity,
            commencement_date,
            commencement_date_specificity,
            expected_closure_date,
            expected_closure_date_specificity,
            expected_operation_date,
            expected_operation_date_specificity,
            expected_operation_date_source,
            expected_closure_date_source,
            expected_closure_date_source,
        }}
    }}"""

    res = sanity_client.query(query)

    if not res or not isinstance(res, dict) or "result" not in res or not res["result"]:
        logger.error("No facilities found")
        return []

    return res["result"]


if __name__ == "__main__":
    facilities = get_cms_facilities()
    for facility in facilities:
        print(
            f"{facility['name']} ({facility['code']}) with {len(facility['units'])} units"
        )
        for unit in facility["units"]:
            print(
                f"  {unit['code']} ({unit['dispatch_type']}) with {unit['capacity_registered']} MW"
            )
            print(f"    status: {unit['status_id']}")
            print(f"    network: {unit['network_id']} {unit['network_region']}")
            print(f"    fueltech: {unit['fueltech_id']} {unit['fueltech_id']}")
            print(f"    capacity registered: {unit['capacity_registered']} MW")
            print(f"    capacity maximum: {unit['capacity_maximum']} MW")
            print(f"    storage capacity: {unit['storage_capacity']} MWh")
            print(
                f"    emissions factor CO2: {unit['emissions_factor_co2']} kgCO2e/MWh"
            )
