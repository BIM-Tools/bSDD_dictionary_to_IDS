import argparse
import requests
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
from collections import defaultdict

BASE_URL = "https://api.bsdd.buildingsmart.org"
FETCH_LIMIT = 500

CLASSIFICATION_MAPPING = {
    'https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3': None,
    'https://identifier.buildingsmart.org/uri/nlsfb/nlsfb2005/2.2': 'NL-SfB 2005',
}

DATATYPE_MAPPING = {
    'String': 'IfcLabel',
    'Boolean': 'IfcBoolean',
    'Integer': 'IfcInteger',
    'Real': 'IfcReal',
    'Character': 'IfcLabel',
    'Time': 'IfcDateTime'
}

PROPERTY_DATATYPE_MAPPING = {
    'https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/AcousticRating': 'IfcLabel',
    'https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/ExposureClass': 'IfcLabel',
    'https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/FireRating': 'IfcLabel',
    'https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/ModelReference': 'IfcLabel',
    'https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/SecurityRating': 'IfcLabel',
    'https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/StrengthClass': 'IfcLabel',
    'https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/StructuralClass': 'IfcLabel',
    'https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/SurfaceSpreadOfFlame': 'IfcLabel',
    'https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/ThermalTransmittance': 'IfcThermalTransmittanceMeasure',
}

BASIC_IFC_ENTITIES = [
    'IfcAirTerminal',
    'IfcAirTerminalBox',
    'IfcAirToAirHeatRecovery',
    'IfcAlarm',
    'IfcBeam',
    'IfcBoiler',
    'IfcBuildingElementProxy',
    'IfcCableCarrierFitting',
    'IfcCableCarrierSegment',
    'IfcCableFitting',
    'IfcCableSegment',
    'IfcChimney',
    'IfcColumn',
    'IfcComnunicationsAppliance',
    'IfcCovering',
    'IfcCurtainWall',
    'IfcDiscreteAccessory',
    'IfcDistributionChamberElement',
    'IfcDoor',
    'IfcElectricAppliance',
    'IfcElementAssembly',
    'IfcEnergyConversionDevice',
    'IfcFireSuppressionTerminal',
    'IfcFlowSegment',
    'IfcFlowStorageDevice',
    'IfcFlowTerminal',
    'IfcFooting',
    'IfcFurniture',
    'IfcGeographicElement',
    'IfcMechanicalFastener',
    'IfcMember',
    'IfcOutlet',
    'IfcPile',
    'IfcPipeFitting',
    'IfcPipeSegment',
    'IfcPlate',
    'IfcRailing',
    'IfcRamp',
    'IfcRampFlight',
    'IfcReinforcingElement',
    'IfcRoof',
    'IfcSanitaryTerminal',
    'IfcSensor',
    'IfcShadingDevice',
    'IfcSign',
    'IfcSignal',
    'IfcSlab',
    'IfcSolarDevice',
    'IfcSpaceHeater',
    'IfcStair',
    'IfcStairFlight',
    'IfcSwitchingDevice',
    'IfcTransportElement',
    'IfcVirtualElement',
    'IfcWall',
    'IfcWindow'
]

classification_map = {}


def get_data_type(dataType, propertyUri):
    if propertyUri in PROPERTY_DATATYPE_MAPPING:
        return PROPERTY_DATATYPE_MAPPING[propertyUri]
    return DATATYPE_MAPPING.get(dataType, 'IFCLABEL')


def split_ifc_bsdd_code(item):
    # Check if the last character is uppercase; if not, return the item without splitting.
    if not item[-1].isupper() or not item[-1].isalpha():
        return item, ""

    # Adjusted logic to find the correct split index, ignoring non-alphabetic characters
    split_index = None
    for i in range(len(item) - 1, 0, -1):
        # Check for transition from lowercase to uppercase among alphabetic characters
        if item[i].isupper() and item[i].isalpha() and item[i-1].islower() and item[i-1].isalpha():
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


def fetch_all_data(endpoint, params={}):
    responses = []
    offset = 0
    limit = FETCH_LIMIT
    params['limit'] = limit

    while True:
        params['offset'] = offset
        response = requests.get(endpoint, params=params)
        if response.status_code != 200:
            print(f"Failed to fetch data: {response.status_code}")
            break
        data = response.json()
        responses.append(data)
        batch_size = len(data.get('results', []))
        if batch_size == 0 or batch_size < limit:
            break
        offset += limit

    return responses


def fetch_classes(base_url, class_uri):
    merged_classes = []
    endpoint = f"{base_url}/api/Dictionary/v1/Classes"
    params = {
        'Uri': class_uri,
        'ClassType': 'Class'
    }

    if params is None:
        params = {}
    all_classes = []
    offset = 0
    limit = FETCH_LIMIT
    params['limit'] = limit

    while True:
        params['offset'] = offset
        response = requests.get(endpoint, params=params)
        if response.status_code != 200:
            print(f"Failed to fetch data: {response.status_code}")
            break
        classes = response.json()
        all_classes = all_classes + [classes]
        fetched_count = len(classes)
        total_count = classes.get('classesTotalCount', 0)
        if fetched_count == 0 or (offset + fetched_count) >= total_count:
            break
        offset += limit

    first_response = None
    for i, response in enumerate(all_classes):
        classes = response.get('classes', [])
        merged_classes.extend(classes)
        if i == 0:
            first_response = response
    if first_response:
        first_response['classes'] = merged_classes
    return first_response


def fetch_properties(base_url, dictionary_uri):
    merged_properties = []
    endpoint = f"{base_url}/api/Dictionary/v1/Properties"
    params = {"Uri": dictionary_uri}
    responses = fetch_all_data(endpoint, params)
    for response in responses:
        properties = response.get('properties', [])
        merged_properties.extend(properties)
    return merged_properties


def fetch_class_details(base_url, class_uri):
    if class_uri in classification_map:
        return classification_map[class_uri]

    endpoint = f"{base_url}/api/Class/v1"
    params = {
        "Uri": class_uri,
        "IncludeClassProperties": True,
        "IncludeClassRelations": True
    }
    response = requests.get(endpoint, params=params)
    if response.status_code != 200:
        print(
            f"Failed to fetch class details: {class_uri}, {response.status_code}")
        return {}
    class_details = response.json()
    classification_map[class_uri] = class_details
    return class_details


def create_classification_element(parent_element, uri_value=None, system_value=None, value_value=None):
    classification = ET.SubElement(parent_element, 'classification', {
        'cardinality': 'required',
        'minOccurs': '1',
        'maxOccurs': '1'
    })

    if uri_value:
        uri = ET.SubElement(classification, 'url')
        simpleValue = ET.SubElement(uri, 'simpleValue')
        simpleValue.text = uri_value

    if system_value:
        system = ET.SubElement(classification, 'system')
        simpleValue = ET.SubElement(system, 'simpleValue')
        simpleValue.text = system_value

    if value_value:
        value = ET.SubElement(classification, 'value')
        simpleValue = ET.SubElement(value, 'simpleValue')
        simpleValue.text = value_value


def create_classification_element_with_options(parent_element, base_uri, values, full_uris):
    values.sort()
    full_uris.sort()

    classification = ET.SubElement(
        parent_element, 'classification', cardinality="required", minOccurs="1", maxOccurs="1")

    system = ET.SubElement(classification, 'system')
    restriction_system = ET.SubElement(
        system, 'xs:restriction', base='xs:string')
    ET.SubElement(restriction_system, 'xs:enumeration', value=base_uri)

    value = ET.SubElement(classification, 'value')
    restriction_value = ET.SubElement(
        value, 'xs:restriction', base="xs:string")
    for val in values:
        ET.SubElement(restriction_value, 'xs:enumeration', value=val)

    url = ET.SubElement(classification, 'url')
    restriction_url = ET.SubElement(url, 'xs:restriction', base="xs:string")
    for uri in full_uris:
        ET.SubElement(restriction_url, 'xs:enumeration', value=uri)


def add_classification_references(class_relations, parent_element):
    grouped_relations = defaultdict(list)
    full_uris_by_base = defaultdict(set)

    for relation in class_relations:
        class_uri = relation.get('relatedClassUri', '')
        classification = fetch_class_details(BASE_URL, class_uri)
        dictionary_uri = classification.get('dictionaryUri', '')
        class_code = classification.get('code', '')
        grouped_relations[dictionary_uri].append(class_code)
        full_uris_by_base[dictionary_uri].add(class_uri)

    for dictionary_uri, values in grouped_relations.items():
        system_name = CLASSIFICATION_MAPPING.get(
            dictionary_uri, dictionary_uri)
        full_uris = list(full_uris_by_base[dictionary_uri])
        if system_name:
            create_classification_element_with_options(
                parent_element, system_name, values, full_uris)


def add_entities(related_ifc_entities, parent_element):
    entity_names, predefined_types = split_ifc_bsdd_code_list(
        related_ifc_entities)

    if len(entity_names) > 0 or len(predefined_types) > 0:
        entity = ET.SubElement(parent_element, 'entity')
        if len(entity_names) > 0:
            name = ET.SubElement(entity, 'name')
            restriction = ET.SubElement(
                name, 'xs:restriction', attrib={'base': 'xs:string'})
            for name in entity_names:
                ET.SubElement(restriction, 'xs:enumeration',
                              attrib={'value': name})

        if len(predefined_types) > 0:
            name = ET.SubElement(entity, 'predefinedType')
            restriction = ET.SubElement(
                name, 'xs:restriction', attrib={'base': 'xs:string'})
            for name in predefined_types:
                ET.SubElement(restriction, 'xs:enumeration',
                              attrib={'value': name})


def add_attribute(property, parent_element):
    atribute_element = ET.SubElement(parent_element, 'attribute')
    atribute_name_element = ET.SubElement(atribute_element, 'name')
    simple_value_element = ET.SubElement(
        atribute_name_element, 'simpleValue')
    simple_value_element.text = property['propertyCode']
    attribute_value_element = ET.SubElement(
        atribute_element, 'value')
    simple_value_element = ET.SubElement(
        attribute_value_element, 'simpleValue')
    simple_value_element.text = property['predefinedValue']


def add_property(property, parent_element):
    property_element = ET.SubElement(parent_element, 'property')
    property_element.set('dataType', get_data_type(
        property['dataType'], property['propertyUri']).upper())

    if 'propertySet' in property:
        property_set_element = ET.SubElement(
            property_element, 'propertySet')
        simple_value_element = ET.SubElement(
            property_set_element, 'simpleValue')
        simple_value_element.text = property['propertySet']

    base_name_element = ET.SubElement(property_element, 'baseName')
    property_name_value = ET.SubElement(
        base_name_element, 'simpleValue')
    property_name_value.text = property['propertyCode']

    if 'allowedValues' in property:
        value_element = ET.SubElement(property_element, 'value')
        xs_restriction = ET.SubElement(
            value_element, 'xs:restriction', base="xs:string")
        for allowed_value in property['allowedValues']:
            ET.SubElement(xs_restriction, 'xs:enumeration',
                          value=allowed_value['value'])
    elif 'predefinedValue' in property:
        value_element = ET.SubElement(property_element, 'value')
        simple_value_element = ET.SubElement(
            value_element, 'simpleValue')
        simple_value_element.text = property['predefinedValue']


def add_properties(class_properties, parent_element):
    for property in class_properties:

        # Seperate IFC entity attributes from properties
        if property['propertySet'] == 'Attributes':
            add_attribute(property, parent_element)
        else:
            add_property(property, parent_element)


def add_global_dictionary_applicability(dictionary_name, specifications):
    specification = ET.SubElement(specifications, 'specification')
    specification.set('ifcVersion', 'IFC4')
    specification.set('name', 'Aanwezigheid ' + dictionary_name)
    applicability = ET.SubElement(specification, 'applicability')
    entity = ET.SubElement(applicability, 'entity')
    restriction = ET.SubElement(
        entity, 'xs:restriction', attrib={'base': 'xs:string'})
    for entity in BASIC_IFC_ENTITIES:
        ET.SubElement(restriction, 'xs:enumeration',
                      attrib={'value': entity.upper()})

    requirements = ET.SubElement(specification, 'requirements')
    create_classification_element(
        requirements, None, dictionary_name)


def add_class_specification(dictionary_name, classification, specifications):
    item = fetch_class_details(BASE_URL, classification['uri'])

    specification = ET.SubElement(specifications, 'specification')
    specification.set('ifcVersion', 'IFC4')
    specification.set('name', item['name'])

    applicability = ET.SubElement(specification, 'applicability')

    create_classification_element(
        applicability, classification['uri'], dictionary_name, item['code'])

    requirements = ET.SubElement(specification, 'requirements')

    add_entities(item.get('relatedIfcEntityNames', []), requirements)

    add_classification_references(
        item.get('classRelations', []), requirements)

    add_properties(item.get('classProperties', []), requirements)


def main(xml_file, dictionary_uri):
    dictionary_with_classes = fetch_classes(BASE_URL, dictionary_uri)

    root = ET.Element('ids', {
        'xmlns:xs': 'http://www.w3.org/2001/XMLSchema',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xsi:schemaLocation': 'http://standards.buildingsmart.org/IDS http://standards.buildingsmart.org/IDS/1.0/ids.xsd',
        'xmlns': 'http://standards.buildingsmart.org/IDS'
    })
    info = ET.SubElement(root, 'info')
    title = ET.SubElement(info, 'title')
    title.text = dictionary_with_classes['name']
    specifications = ET.SubElement(root, 'specifications')

    add_global_dictionary_applicability(
        dictionary_with_classes['name'], specifications)

    for classification in dictionary_with_classes['classes']:
        add_class_specification(
            dictionary_with_classes['name'], classification, specifications)

    # Pretty print the XML
    xml_str = ET.tostring(root, encoding='utf-8', method='xml')
    dom = parseString(xml_str)
    xml_str = dom.toprettyxml(indent="  ")

    with open(xml_file, 'w', encoding='utf-8') as file:
        file.write(xml_str)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate IDS file from bSDD dictionary URI",
        epilog="Example command: python bsdd_to_ids.py basis_bouwproducten_oene.ids https://identifier.buildingsmart.org/uri/volkerwesselsbvgo/basis_bouwproducten_oene/latest"
    )
    parser.add_argument("ids_file_path", type=str,
                        help="The filepath for the IDS file")
    parser.add_argument("dictionary_uri", type=str,
                        help="The URI for the dictionary")

    args = parser.parse_args()

    main(args.ids_file_path, args.dictionary_uri)
