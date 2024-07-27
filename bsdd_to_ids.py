import argparse
import hashlib
import json
import os
import requests
from collections import defaultdict
from tqdm import tqdm
from ifctester import ids, reporter

BASE_URL = "https://api.bsdd.buildingsmart.org"
FETCH_LIMIT = 1000

IFC_VERSIONS = "IFC4X3_ADD2"  # 'IFC4 IFC4X3_ADD2'

INCLUDEDRELATIONTYPES = [
    "HasMaterial",
    # "HasReference",
    "IsEqualTo",
    # "IsSimilarTo",
    # "IsParentOf",
    "IsChildOf",
    # "HasPart",
    "IsPartOf",
]

DATATYPE_MAPPING = {
    "String": "IfcLabel",
    "Boolean": "IfcBoolean",
    "Integer": "IfcInteger",
    "Real": "IfcReal",
    "Character": "IfcLabel",
    "Time": "IfcDateTime",
}

PROPERTY_DATATYPE_MAPPING = {
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/AcousticRating": "IfcLabel",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/CapacityPeople": "IfcCountMeasure",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/ClearDepth": "IfcPositiveLengthMeasure",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/ClearHeight": "IfcPositiveLengthMeasure",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/ClearWidth": "IfcPositiveLengthMeasure",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/ExposureClass": "IfcLabel",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/FireRating": "IfcLabel",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/Height": "IfcPositiveLengthMeasure",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/ModelReference": "IfcLabel",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/SecurityRating": "IfcLabel",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/StrengthClass": "IfcLabel",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/StructuralClass": "IfcLabel",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/SurfaceSpreadOfFlame": "IfcLabel",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/ThermalTransmittance": "IfcThermalTransmittanceMeasure",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/TileLength": "IfcPositiveLengthMeasure",
    "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/TileWidth": "IfcPositiveLengthMeasure",
}

BASIC_IFC_ENTITIES = [
    "IfcAirTerminal",
    "IfcAirTerminalBox",
    "IfcAirToAirHeatRecovery",
    "IfcAlarm",
    "IfcBeam",
    "IfcBoiler",
    "IfcBuildingElementProxy",
    "IfcCableCarrierFitting",
    "IfcCableCarrierSegment",
    "IfcCableFitting",
    "IfcCableSegment",
    "IfcChimney",
    "IfcColumn",
    "IfcComnunicationsAppliance",
    "IfcCovering",
    "IfcCurtainWall",
    "IfcDiscreteAccessory",
    "IfcDistributionChamberElement",
    "IfcDoor",
    "IfcElectricAppliance",
    "IfcElementAssembly",
    "IfcEnergyConversionDevice",
    "IfcFireSuppressionTerminal",
    "IfcFlowSegment",
    "IfcFlowStorageDevice",
    "IfcFlowTerminal",
    "IfcFooting",
    "IfcFurniture",
    "IfcGeographicElement",
    "IfcMechanicalFastener",
    "IfcMember",
    "IfcOutlet",
    "IfcPile",
    "IfcPipeFitting",
    "IfcPipeSegment",
    "IfcPlate",
    "IfcRailing",
    "IfcRamp",
    "IfcRampFlight",
    "IfcReinforcingElement",
    "IfcRoof",
    "IfcSanitaryTerminal",
    "IfcSensor",
    "IfcShadingDevice",
    "IfcSign",
    "IfcSignal",
    "IfcSlab",
    "IfcSolarDevice",
    "IfcSpaceHeater",
    "IfcStair",
    "IfcStairFlight",
    "IfcSwitchingDevice",
    "IfcTransportElement",
    "IfcVirtualElement",
    "IfcWall",
    "IfcWindow",
]

dictionary_map = {}
classification_map = {}


def url_to_filename(url):
    """Hashes a URL string to create a unique filename-safe identifier.

    Args:
        url (str): The URL string to hash.

    Returns:
        str: A filename-safe hash of the URL string.
    """
    hashed_filename = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return hashed_filename


def get_data_type(dataType, propertyUri):
    if propertyUri in PROPERTY_DATATYPE_MAPPING:
        return PROPERTY_DATATYPE_MAPPING[propertyUri]
    return DATATYPE_MAPPING.get(dataType, "IFCLABEL")


def split_ifc_bsdd_code(item):
    # Check if the last character is uppercase; if not, return the item without splitting.
    if not item[-1].isupper() or not item[-1].isalpha():
        return item, ""

    # Adjusted logic to find the correct split index, ignoring non-alphabetic characters
    split_index = None
    for i in range(len(item) - 1, 0, -1):
        # Check for transition from lowercase to uppercase among alphabetic characters
        if (
            item[i].isupper()
            and item[i].isalpha()
            and item[i - 1].islower()
            and item[i - 1].isalpha()
        ):
            split_index = i
            break

    if split_index:
        return item[:split_index], item[split_index:]
    else:
        return item, ""


def split_ifc_bsdd_code_list(entity_nameslist):
    entity_names_set = set()
    predefined_types_set = set()

    for item in entity_nameslist:
        entity_name, predefined_type = split_ifc_bsdd_code(item)
        entity_names_set.add(entity_name.upper())
        if predefined_type:
            predefined_types_set.add(predefined_type.upper())

    return list(entity_names_set), list(predefined_types_set)


def fetch_all_paginated(endpoint, params={}):
    responses = []
    offset = 0
    limit = FETCH_LIMIT
    params["limit"] = limit

    while True:
        params["offset"] = offset
        response = requests.get(endpoint, params=params)
        if response.status_code != 200:
            print(f"Failed to fetch data: {response.status_code}")
            break
        data = response.json()
        responses.append(data)
        batch_size = len(data.get("results", []))
        if batch_size == 0 or batch_size < limit:
            break
        offset += limit

    return responses


def fetch_dictionary(base_url, dictionary_uri, use_cache):
    if dictionary_uri in dictionary_map:
        return dictionary_map[dictionary_uri]

    if use_cache:
        filename_safe_uri = url_to_filename(dictionary_uri)
        temp_filename = os.path.join("cache", f"dictionary_{filename_safe_uri}.json")
        if os.path.isfile(temp_filename):
            with open(temp_filename, "r") as f:
                return json.load(f)

    endpoint = f"{base_url}/api/Dictionary/v1"
    params = {"Uri": dictionary_uri, "IncludeTestDictionaries": True}
    response = requests.get(endpoint, params=params)
    if response.status_code != 200:
        print(f"Failed to fetch dictionary: {response.status_code}")
        return None
    data = response.json()
    dictionaries = data.get("dictionaries", [])

    if use_cache and dictionaries:
        with open(temp_filename, "w") as f:
            json.dump(dictionaries[0], f)

    if dictionaries:
        return dictionaries[0]
    else:
        return None


def fetch_classes(base_url, dictionary_uri, use_cache):

    if use_cache:
        filename_safe_uri = url_to_filename(dictionary_uri)
        temp_filename = os.path.join(
            "cache", f"dictionary_classes_{filename_safe_uri}.json"
        )
        if os.path.isfile(temp_filename):
            with open(temp_filename, "r") as f:
                return json.load(f)

    merged_classes = []
    endpoint = f"{base_url}/api/Dictionary/v1/Classes"
    params = {"Uri": dictionary_uri, "ClassType": "Class"}

    if params is None:
        params = {}
    all_classes = []
    offset = 0
    limit = FETCH_LIMIT
    params["limit"] = limit

    while True:
        params["offset"] = offset
        response = requests.get(endpoint, params=params)
        if response.status_code != 200:
            print(f"Failed to fetch data: {response.status_code}")
            break
        classes = response.json()
        all_classes = all_classes + [classes]
        fetched_count = len(classes)
        total_count = classes.get("classesTotalCount", 0)
        if fetched_count == 0 or (offset + fetched_count) >= total_count:
            break
        offset += limit

    dictionary_classes = None
    for i, response in enumerate(all_classes):
        classes = response.get("classes", [])
        merged_classes.extend(classes)
        if i == 0:
            dictionary_classes = response
    if dictionary_classes:
        dictionary_classes["classes"] = merged_classes

    if use_cache and dictionary_classes:
        with open(temp_filename, "w") as f:
            json.dump(dictionary_classes, f)

    return dictionary_classes


def fetch_class_details(base_url, class_uri, use_cache):
    if class_uri in classification_map:
        return classification_map[class_uri]

    if use_cache:
        filename_safe_uri = url_to_filename(class_uri)
        temp_filename = os.path.join("cache", f"class_{filename_safe_uri}.json")
        if os.path.isfile(temp_filename):
            with open(temp_filename, "r") as f:
                return json.load(f)

    endpoint = f"{base_url}/api/Class/v1"
    params = {
        "Uri": class_uri,
        "IncludeClassProperties": True,
        "IncludeClassRelations": True,
    }
    response = requests.get(endpoint, params=params)
    if response.status_code != 200:
        print(f"Failed to fetch class: {class_uri}, {response.status_code}")
        return None
    class_details = response.json()
    classification_map[class_uri] = class_details
    if use_cache and class_details:
        with open(temp_filename, "w") as f:
            json.dump(class_details, f)
    return class_details


def create_classification_facet_with_options(
    parent_element, base_uri, values, full_uris
):
    if len(values) == 1:
        restriction_value = values[0]
    elif len(values) > 0:
        values.sort()
        restriction_value = ids.Restriction(options={"enumeration": values})

    uri = None
    if len(full_uris) == 1:
        uri = full_uris[0]

    classification = ids.Classification(restriction_value, base_uri, uri)
    parent_element.append(classification)


def group_class_relations_by_dictionary(class_relations, use_cache):
    grouped_relations = defaultdict(list)
    full_uris_by_base = defaultdict(set)
    for relation in class_relations:
        if relation.get("RelationType") not in INCLUDEDRELATIONTYPES:
            continue
        class_uri = relation.get("relatedClassUri")
        if not class_uri:
            continue

        classification = fetch_class_details(BASE_URL, class_uri, use_cache)
        if not classification:
            continue

        dictionary_uri = classification.get("dictionaryUri", "")
        class_code = classification.get("code", "")
        grouped_relations[dictionary_uri].append(class_code)
        full_uris_by_base[dictionary_uri].add(class_uri)

    return grouped_relations, full_uris_by_base


def add_classification_facets(
    parent_element, grouped_relations, full_uris_by_base, use_cache
):
    for dictionary_uri, class_codes in grouped_relations.items():

        # Don't include IFC as classification
        if (
            "https://identifier.buildingsmart.org/uri/buildingsmart/ifc"
            in dictionary_uri
        ):
            continue

        dictionary = fetch_dictionary(BASE_URL, dictionary_uri, use_cache)
        if dictionary:
            system_name = dictionary.get("name")
            if system_name:
                full_uris = list(full_uris_by_base[dictionary_uri])
                create_classification_facet_with_options(
                    parent_element, system_name, class_codes, full_uris
                )


def add_classification_references(class_relations, parent_element, use_cache):
    grouped_relations, full_uris_by_base = group_class_relations_by_dictionary(
        class_relations, use_cache
    )
    add_classification_facets(
        parent_element, grouped_relations, full_uris_by_base, use_cache
    )


def add_entity_facet(related_ifc_entities, parent_element):
    entity_names, predefined_types = split_ifc_bsdd_code_list(related_ifc_entities)

    if len(entity_names) > 0 or len(predefined_types) > 0:
        name = None
        predefined_type = None

        if len(entity_names) == 1:
            name = entity_names[0]
        elif len(entity_names) > 0:
            name = ids.Restriction(options={"enumeration": entity_names})
        if len(predefined_types) == 1:
            predefined_type = predefined_types[0]
        elif len(predefined_types) > 0:
            predefined_type = ids.Restriction(options={"enumeration": predefined_types})
        parent_element.append(ids.Entity(name, predefined_type))


def add_attribute_facet(property, parent_element):
    if not property["predefinedValue"]:
        return

    parent_element.append(
        ids.Attribute(property["propertyCode"], property["predefinedValue"])
    )


def add_property_facet(bsdd_property, parent_element):
    required_keys = {"propertySet", "propertyCode"}
    if not all(key in bsdd_property for key in required_keys):
        return

    value = None
    if "allowedValues" in bsdd_property:
        value = ids.Restriction(
            options={
                "enumeration": list(
                    map(lambda x: x["value"], bsdd_property["allowedValues"])
                )
            }
        )
    elif "predefinedValue" in bsdd_property:
        value = bsdd_property["predefinedValue"]

    property_facet = ids.Property(
        bsdd_property["propertySet"],
        bsdd_property["propertyCode"],
        value,
        get_data_type(bsdd_property["dataType"], bsdd_property["propertyUri"]).upper(),
        bsdd_property["propertyUri"],
    )
    parent_element.append(property_facet)


def add_properties(class_properties, parent_element):
    for property in class_properties:

        # Separate IFC entity attributes from properties
        if property["propertySet"] == "Attributes":
            add_attribute_facet(property, parent_element)
        else:
            add_property_facet(property, parent_element)


def add_global_dictionary_applicability(dictionary_name, dictionary_uri, ids_document):
    specification = ids.Specification(
        name=f"Presence of {dictionary_name}",
        ifcVersion=IFC_VERSIONS,
        description=f"Ensures that all applicable objects in the model have a classification from the '{dictionary_name}' bSDD dictionary: {dictionary_uri}",
    )

    name = ids.Restriction(
        options={"enumeration": list(map(lambda x: x.upper(), BASIC_IFC_ENTITIES))}
    )
    entity = ids.Entity(name)
    classification = ids.Classification(system=dictionary_name)
    specification.requirements.append(classification)
    specification.applicability.append(entity)
    ids_document.specifications.append(specification)


def add_class_specification(dictionary_name, dictionary_class, ids_document, use_cache):
    class_details = fetch_class_details(BASE_URL, dictionary_class["uri"], use_cache)

    if not class_details:
        return

    specification = ids.Specification(
        name=class_details["name"],
        ifcVersion=IFC_VERSIONS,
        description=f"Verifies that each object classified as '{class_details['name']}' meets the requirements from the bSDD class: {dictionary_class['uri']}",
    )

    # TODO check why uri is not accepted by IfcTester
    classification = ids.Classification(
        value=class_details["code"], system=dictionary_name, uri=dictionary_class["uri"]
    )
    specification.applicability.append(classification)

    requirements = specification.requirements

    add_entity_facet(class_details.get("relatedIfcEntityNames", []), requirements)

    add_classification_references(
        class_details.get("classRelations", []), requirements, use_cache
    )

    add_properties(class_details.get("classProperties", []), requirements)

    ids_document.specifications.append(specification)


def get_date(date_time_string):
    if date_time_string:
        return date_time_string.split("T")[0]
    else:
        return None


def convert_to_version_097(ids_string):
    ids_string = ids_string.replace(
        "http://standards.buildingsmart.org/IDS http://standards.buildingsmart.org/IDS/1.0/ids.xsd",
        "http://standards.buildingsmart.org/IDS http://standards.buildingsmart.org/IDS/0.9.7/ids.xsd",
    )
    ids_string = ids_string.replace(
        "IFC4X3_ADD2",
        "IFC4X3",
    )
    return ids_string


def to_xml(xml_string, filepath):
    with open(filepath, "wb") as f:
        f.write(
            f"<?xml version='1.0' encoding='utf-8'?>\n{xml_string}\n".encode("utf-8")
        )


def main(xml_file, dictionary_uri, ids_version, use_cache):
    dictionary_with_classes = fetch_classes(BASE_URL, dictionary_uri, use_cache)

    ids_document = ids.Ids(
        title=dictionary_with_classes["name"],
        copyright=dictionary_with_classes["organizationNameOwner"],
        version=dictionary_with_classes["version"],
        description=f'IDS for bSDD dictionary {dictionary_with_classes["name"]}',
        date=get_date(dictionary_with_classes["lastUpdatedUtc"]),
    )

    add_global_dictionary_applicability(
        dictionary_with_classes["name"], dictionary_uri, ids_document
    )

    for classification in tqdm(dictionary_with_classes["classes"]):
        add_class_specification(
            dictionary_with_classes["name"],
            classification,
            ids_document,
            use_cache,
        )

    if ids_version == "0.9.7":
        ids_string = ids_document.to_string()
        to_xml(convert_to_version_097(ids_string), xml_file)

    else:
        ids_document.to_xml(xml_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate IDS file from bSDD dictionary URI",
        epilog="Example command: python bsdd_to_ids.py basis_bouwproducten_oene.ids https://identifier.buildingsmart.org/uri/volkerwesselsbvgo/basis_bouwproducten_oene/latest",
    )
    parser.add_argument("ids_file_path", type=str, help="The filepath for the IDS file")
    parser.add_argument("dictionary_uri", type=str, help="The URI for the dictionary")
    parser.add_argument(
        "-v",
        "--version",
        type=str,
        nargs="?",
        default="1.0",
        choices=["1.0", "0.9.7"],
        help="The IDS version (default: 1.0)",
    )
    parser.add_argument(
        "-c", "--use_cache", action="store_true", default=False, help="Use local cache"
    )

    args = parser.parse_args()

    main(args.ids_file_path, args.dictionary_uri, args.version, args.use_cache)
