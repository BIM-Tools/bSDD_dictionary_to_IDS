# bSDD_dictionary_to_IDS

Convert a bSDD Dictionary into an IDS

## Description

This Python script facilitates the conversion of buildingSMART Data Dictionary (bSDD) entries into a Information Delivery Specification (IDS) file.

Helps with validation of BIM models against bSDD specifications, streamlining compliance checks and quality assurance workflows.

## Installation

Clone this repository to your local machine using:

```bash
git clone https://github.com/BIM-Tools/bSDD_dictionary_to_IDS.git
```

Navigate to the project directory.

## Usage

To convert a bSDD dictionary into an IDS file, follow these steps:

1. **Find a Dictionary URI**:

   - Visit [buildingSMART Data Dictionary Search](https://search.bsdd.buildingsmart.org/).
   - Navigate through "List organizations" to find a specific dictionary version.
   - The Dictionary URI is typically in the format of `https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3`, without any class at the end.

2. **Run the Script**:
   - Ensure Python is installed on your system.
   - Use the following command, replacing `<ids_file_path>` with your desired output file path, `<dictionary_uri>` with the URI you found, and optionally specifying the IDS version with `-v` or `--version`:
     `python bsdd_to_ids.py <ids_file_path> <dictionary_uri> [-v VERSION]`

### Example Command

Here is an example command that demonstrates how to run the script:

```bash
python bsdd_to_ids.py basis_bouwproducten_oene.ids https://identifier.buildingsmart.org/uri/volkerwesselsbvgo/basis_bouwproducten_oene/latest
```

## Help

```bash
usage: bsdd_to_ids.py [-h] ids_file_path dictionary_uri [-v VERSION]

Generate IDS file from bSDD dictionary URI

positional arguments:
  ids_file_path         The filepath for the IDS file
  dictionary_uri        The URI for the dictionary

options:
  -h, --help            show this help message and exit

Example command: python bsdd_to_ids.py basis_bouwproducten_oene.ids https://identifier.buildingsmart.org/uri/volkerwesselsbvgo/basis_bouwproducten_oene/latest -v 1.0
```

## Contributing

Contributions to improve the script or extend its functionality are welcome. Please refer to the contributing guidelines for more information.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
