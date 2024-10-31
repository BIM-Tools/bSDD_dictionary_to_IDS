import argparse
import json
import re
from datetime import datetime
from ifctester import open as open_ids

# Mapping dictionary for data types
DATA_TYPE_MAPPING = {
    "IFCLABEL": "String",
    "IFCINTEGER": "Integer",
    "IFCBOOLEAN": "Boolean",
    "IFCREAL": "Real",
    "IFCIDENTIFIER": "String",
    "IFCURIREFERENCE": "String",
    "IFCTEXT": "String",
    "IFCTIME": "Time",
    "IFCDATE": "Date",
    "IFCDATETIME": "Date",
    "IFCDURATION": "String",
    "IFCTIMESTAMP": "Time"
}

dictionary_properties = {}


def convert_specification_to_class(spec):
    class_data = {
        "ClassType": "Class",
        "Name": spec["@name"],
        "Code": code_from_name(spec["@name"]),
        "Definition": spec.get("@description", ""),
    }
    ifc_entity_applicability = get_ifc_entity(spec["applicability"])
    ifc_entity_requirements = get_ifc_entity(spec["requirements"])
    if ifc_entity_applicability:
        class_data["RelatedIfcEntityNamesList"] = ifc_entity_applicability
    elif ifc_entity_requirements:
        class_data["RelatedIfcEntityNamesList"] = ifc_entity_requirements

    properties = get_properties(spec["applicability"])
    properties = properties+get_properties(spec["requirements"])

    if (len(properties) > 0):
        class_data["ClassProperties"] = properties

    classifications = get_classifications(spec["applicability"])
    classifications = classifications+get_classifications(spec["requirements"])

    if (len(classifications) > 0):
        class_data["ClassRelations"] = classifications

    return class_data


def convert_date_to_utc_timestamp(date_str):
    date_obj = datetime.fromisoformat(date_str)
    return date_obj.isoformat() + "Z"


def code_from_name(name):
    name = name.replace(' ', '')
    return re.sub(r'[^a-zA-Z0-9_-]', '', name)


def get_ifc_entity(ruleset):
    related_ifc_entity_names = []
    if "entity" in ruleset:
        entity = ruleset["entity"][0]
        related_ifc_entity_name = ""
        if "name" in entity:
            if "simpleValue" in entity["name"]:
                related_ifc_entity_name = related_ifc_entity_name + \
                    entity["name"]["simpleValue"]
        if "predefinedType" in entity:
            if "simpleValue" in entity["predefinedType"]:
                related_ifc_entity_name = related_ifc_entity_name + \
                    entity["predefinedType"]["simpleValue"]
        if related_ifc_entity_name != "":
            related_ifc_entity_names.append(
                related_ifc_entity_name.replace('.', ''))
    return related_ifc_entity_names


def get_property(property):
    data_type = property.get("@dataType", "")
    mapped_data_type = DATA_TYPE_MAPPING.get(data_type, "String")

    owned_uri = None
    property_uri = None
    uri = property.get("@uri", None)
    if uri != None:
        if uri.startswith("https://identifier.buildingsmart.org/uri/"):
            property_uri = uri
        else:
            owned_uri = uri

    class_property = {
        "Code": code_from_name(property["baseName"]["simpleValue"]),
        "Description": property.get("@instructions", ""),
        "IsRequired": property.get("@cardinality", "") == "required",
        "PropertySet": property["propertySet"]["simpleValue"]
    }
    if (owned_uri != None):
        class_property["OwnedUri"] = owned_uri

    if (property_uri != None):
        class_property["PropertyUri"] = property_uri
    else:
        property_code = code_from_name(property["baseName"]["simpleValue"])
        class_property["PropertyCode"] = property_code
        dictionary_property = {
            "Code": property_code,
            "Name": property["baseName"]["simpleValue"],
            "Definition": property.get("@instructions", ""),
            "DataType": mapped_data_type,
        }
        if (owned_uri != None):
            dictionary_property["OwnedUri"] = owned_uri
        if property_code not in dictionary_properties.keys():
            dictionary_properties[property_code] = dictionary_property

    allowed_values = []
    if "value" in property and "xs:restriction" in property["value"]:
        for index, enum in enumerate(property["value"]["xs:restriction"][0]["xs:enumeration"]):
            allowed_value = {
                "Code": code_from_name(enum["@value"]),
                "Value": enum["@value"],
                "SortNumber": index
            }
            allowed_values.append(allowed_value)
    if len(allowed_values) > 0:
        class_property["AllowedValues"] = allowed_values

    return class_property


def get_classifications(ruleset):
    class_relations = []
    if "classification" in ruleset:
        for classification in ruleset["classification"]:
            if "value" in classification and "xs:restriction" in classification["value"]:
                for pattern in classification["value"]["xs:restriction"][0]["xs:pattern"]:
                    classCode = pattern['@value'].replace('.*', '')
                    class_relation = {
                        "RelationType": "IsChildOf",
                        "RelatedClassUri": f"https://identifier.buildingsmart.org/uri/nlsfb/nlsfb2005/2.2/class/{classCode}"
                    }
                    class_relations.append(class_relation)
    return class_relations


def get_properties(ruleset):
    class_properties = []
    if "property" in ruleset:
        for property in ruleset["property"]:
            class_property = get_property(property)
            class_properties.append(class_property)
    return class_properties


def remove_none_and_empty_values(d):
    if isinstance(d, dict):
        return {k: remove_none_and_empty_values(v) for k, v in d.items() if v not in [None, ""]}
    elif isinstance(d, list):
        return [remove_none_and_empty_values(v) for v in d if v not in [None, ""]]
    else:
        return d
    
def main(input_file, output_file, organization_code, change_request_email):
    xml_file = input_file
    ids_document = open_ids(xml_file, validate=False)
    ids_data = ids_document.asdict()

    info = ids_data["info"]
    release_date = convert_date_to_utc_timestamp(info["date"])

    dictionary_classes = []

    for spec in ids_data["specifications"]["specification"]:
        class_data = convert_specification_to_class(spec)
        dictionary_classes.append(class_data)

    bsdd_data = {
        "ModelVersion": "2.0",
        "OrganizationCode": organization_code,
        "DictionaryCode": code_from_name(info["title"]),
        "DictionaryName": info["title"],
        "DictionaryVersion": "0.1",
        "LanguageIsoCode": "nl-NL",
        "UseOwnUri": None,  # bool
        "DictionaryUri": None,
        "License": None,
        "LicenseUrl": None,
        "ChangeRequestEmailAddress": change_request_email,
        "MoreInfoUrl": None,
        "QualityAssuranceProcedure": None,
        "QualityAssuranceProcedureUrl": None,
        "ReleaseDate": release_date,
        "Status": "Preview",
        "Classes": dictionary_classes,
        "Properties": list(dictionary_properties.values())
    }

    bsdd_data = remove_none_and_empty_values(bsdd_data)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(bsdd_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert IDS to bSDD JSON format.",
        epilog="Example command: python ids_to_bsdd.py example/11316_ids_ODUMtestbouwproducten_Beoordeling.ids example/11316_ids_ODUMtestbouwproducten_Beoordeling_bsdd.json volkerwesselsbvgo --change_request_email rvdscheur@digibase.nl",
    )
    parser.add_argument("input_file", help="Path to the input IDS file. Example: example/11316_ids_ODUMtestbouwproducten_Beoordeling.ids")
    parser.add_argument("output_file", help="Path to the output JSON file. Example: example/11316_ids_ODUMtestbouwproducten_Beoordeling_bsdd.json")
    parser.add_argument("organization_code", help="Organization code. Example: org_code")
    parser.add_argument("--change_request_email", help="Change request email address. Example: email@example.com", default=None)
    args = parser.parse_args()

    main(
        args.input_file,
        args.output_file,
        args.organization_code,
        args.change_request_email,
    )