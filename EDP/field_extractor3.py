import requests
import json
import pandas as pd
import os
import tqdm as tqdm
import requests
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote_plus
import rdflib
import os
from rdflib.namespace import RDF, DC, Namespace
import xml.etree.ElementTree as ET
from lxml import etree
import random
import io

# directory = '/Users/suhaibbasir/Documents/CS/MSc/Thesis/Thesis/EDP/test'  # Change this to your directory containing RDF/XML files
# Define namespace mappings
# Define the namespaces
namespaces = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
    'edm': 'http://www.europeana.eu/schemas/edm/',
    'skos': 'http://www.w3.org/2004/02/skos/core#',
    'foaf': 'http://xmlns.com/foaf/0.1/',
    'ore': 'http://www.openarchives.org/ore/terms/',
    'dqv': 'http://www.w3.org/ns/dqv#',
    'oa': 'http://www.w3.org/ns/oa#'
}

# Define functions to find elements
def find_single_element_text(tree, xpath_query):
    element = tree.find(xpath_query, namespaces)
    if element is not None:
        resource = element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
        if resource:
            # print("Resource found for:", xpath_query)
            # Find the corresponding element using rdf:about attribute
            linked_element = tree.find(f".//*[@rdf:about='{resource}']", namespaces)
            if linked_element is not None:
                # Extract text content of skos:prefLabel within the linked element
                label = linked_element.find('skos:prefLabel', namespaces)
                if label is not None:
                    return label.text
            return resource  # Fallback to the resource URI if linked element not found
        else:
            return element.text
    return None

def find_multiple_elements_text(tree, xpath_query):
    elements = tree.findall(xpath_query, namespaces)
    results = {}
    for element in elements:
        if elements:
            for element in elements:
                # Check if the element has an xml:lang attribute
                language_tag = element.get('{http://www.w3.org/XML/1998/namespace}lang', 'default')  # 'default' if no lang

                # Check if the element has a reference to a resource
                resource_ref = element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')

                if resource_ref:
                    # Find the element with rdf:about matching the resource reference
                    resource_element = tree.xpath(f"//*[@rdf:about='{resource_ref}']", namespaces=namespaces)
                    if resource_element:
                        # Get the skos:prefLabel and skos:altLabel from the resource element
                        pref_labels = resource_element[0].xpath("skos:prefLabel", namespaces=namespaces)
                        alt_labels = resource_element[0].xpath("skos:altLabel", namespaces=namespaces)

                        # Combine both prefLabel and altLabel in one list
                        all_labels = pref_labels + alt_labels

                        for label in all_labels:
                            # Get the label text and the xml:lang attribute
                            label_text = label.text
                            label_lang = label.get('{http://www.w3.org/XML/1998/namespace}lang', 'default')

                            # Append the text to the corresponding language in the results dictionary
                            if label_lang in results:
                                results[label_lang].append(label_text)
                            else:
                                results[label_lang] = [label_text]
                else:
                    # Add the text content of the element if no resource reference or labels are found
                    if language_tag in results:
                        results[language_tag].append(element.text)
                    else:
                        results[language_tag] = [element.text]
    return results


def find_tier_information(tree, namespaces):
    # Initialize variables to store tier information
    content_tier = None
    metadata_tier = None

    # Find all hasBody elements
    has_body_elements = tree.findall('.//oa:hasBody', namespaces)

    for element in has_body_elements:
        resource = element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', '')
        
        # Check for content tier
        if 'contentTier' in resource:
            content_tier = resource.split('contentTier')[-1]
        
        # Check for metadata tier
        elif 'metadataTier' in resource:
            metadata_tier = resource.split('metadataTier')[-1]

    return content_tier, metadata_tier

def find_with_condition(condition, search, tree, namespaces, lang=None):
    # Find all <ore:Proxy> elements with rdf:about containing the condition
    paths = tree.xpath(f"//ore:Proxy[contains(@rdf:about, '{condition}')]", namespaces=namespaces)
    
    # Initialize a dictionary to store results based on language
    results = {}

    languages = ["en", "bg", "cs", "da", "de", "es", "et", "fi", "fr", "hr", "hu", "it", "lt", "nl", "pl", "pt", "ro", "sk", "sl", "sv"]
    
    # Check if we found the <ore:Proxy> elements
    if paths:
        for path in paths:
            # Build the XPath query with an optional language filter
            if lang:
                elements = path.xpath(f"{search}[@xml:lang='{lang}']", namespaces=namespaces)
            else:
                elements = path.xpath(f"{search}", namespaces=namespaces)
                # Check if any of these elements have lang='en'
                # en_elements = path.xpath(f"{search}[@xml:lang='en']", namespaces=namespaces)
                # if en_elements:
                #     for en_element in en_elements:print(en_element.text)
                #     print("AAAA")
                #     continue  # Skip this iteration if any elements with lang='en' are found

            if elements:
                for element in elements:
                    # Check if the element has an xml:lang attribute
                    language_tag = element.get('{http://www.w3.org/XML/1998/namespace}lang', 'default')  # 'default' if no lang

                    # Check if the element has a reference to a resource
                    resource_ref = element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
                        
                    if language_tag == "en" and not resource_ref and lang is None and condition == "/europeana":
                        continue

                    if resource_ref:
                        # Find the element with rdf:about matching the resource reference
                        resource_element = tree.xpath(f"//*[@rdf:about='{resource_ref}']", namespaces=namespaces)
                        if resource_element:
                            # Get the skos:prefLabel and skos:altLabel from the resource element
                            pref_labels = resource_element[0].xpath("skos:prefLabel", namespaces=namespaces)
                            alt_labels = resource_element[0].xpath("skos:altLabel", namespaces=namespaces)

                            # Combine both prefLabel and altLabel in one list
                            all_labels = pref_labels + alt_labels

                            for label in all_labels:
                                # Get the label text and the xml:lang attribute
                                label_text = label.text
                                label_lang = label.get('{http://www.w3.org/XML/1998/namespace}lang', 'default')

                                if label_lang in languages or label_lang == "default":
                                    # print("idk bruh :", label_lang in languages)
                                    # Append the text to the corresponding language in the results dictionary
                                    if label_lang in results:
                                        results[label_lang].append(label_text)
                                    else:
                                        results[label_lang] = [label_text]
                    else:
                        # Add the text content of the element if no resource reference or labels are found
                        if language_tag in languages or language_tag == "default":
                            if language_tag in results:
                                results[language_tag].append(element.text)
                            else:
                                results[language_tag] = [element.text]

    else:
        print(f'No matching ore:Proxy element found')
    
    # Return the dictionary of results, or None if no matches
    return results if results else None


def check_if_translated(europeana_id):
    try:
        # Extract the last part of the europeana_id
        last_part = europeana_id.split('/')[-1]
        first_part = europeana_id.split('/')[-2]
        
        # Construct the file path for the translation CSV
        translation_subdirectory = first_part + '.csv'
        csv_path = f'/home/sbasir/Thesis/Thesis/EDP/sample_data/translations/{translation_subdirectory}'
        
        # Check if the CSV file exists
        if not os.path.exists(csv_path):
            # Return False if the file does not exist
            print(f"{csv_path} does not exist")
            return False
        
        # Load the CSV file
        translation_csv = pd.read_csv(csv_path)
        
        # Check if the last_part is in the 'item_id' column of the DataFrame
        translated = last_part in translation_csv['item_id'].values
        
        # Return True if found, False otherwise
        return translated

    except FileNotFoundError:
        # If the file is not found, print an error message and return False
        print(f"File not found: {csv_path}")
        return False

    except Exception as e:
        # Catch all other exceptions, print an error message, and return False
        print(f"Error checking translation for {europeana_id}: {e}")
        return False

def generate_solr_xml(data):
    solr_docs = "<add>"
    
    # Add the top-level fields first (e.g., dcterms:modified, edm:type)
    solr_docs += f'<field name="europeana_id">{data["europeana_id"]}</field>'
    solr_docs += f'<field name="timestamp_update">{data["dcterms:modified"]}</field>'
    solr_docs += f'<field name="edm:type">{data["edm:type"]}</field>'
    solr_docs += f'<field name="content_tier">{data["contentTier"]}</field>'
    solr_docs += f'<field name="metadata_tier">{data["metadataTier"]}</field>'


    # Function to add fields with language variants
    def add_field_with_lang(field_name, lang_values):
        nonlocal solr_docs
        if lang_values:
            solr_docs += f'<field name="{field_name}">'
            for lang, values in lang_values.items():
                for value in values:
                    if lang == 'default':
                        solr_docs += f'<value>{value}</value>'  # No language tag
                    else:
                        solr_docs += f'<value lang="{lang}">{value}</value>'  # With language tag
            solr_docs += '</field>'

    # Add provided_data section
    solr_docs += "<provided_data>"
    provided_data = data.get('provided_data', {})
    for field, values in provided_data.items():
        if isinstance(values, dict):  # Handle language variants
            add_field_with_lang(field, values)
        elif values:  # Handle fields without language variants
            solr_docs += f'<field name="{field}">{values}</field>'
    solr_docs += "</provided_data>"

    # Add enriched_data section
    solr_docs += "<enriched_data>"
    enriched_data = data.get('enriched_data', {})
    for field, values in enriched_data.items():
        if isinstance(values, dict):  # Handle language variants
            add_field_with_lang(field, values)
    solr_docs += "</enriched_data>"

    # Add translated_data section
    solr_docs += "<translated_data>"
    translated_data = data.get('translated_data', {})
    for field, values in translated_data.items():
        if isinstance(values, dict):  # Handle language variants
            add_field_with_lang(field, values)
    solr_docs += "</translated_data>"

    solr_docs += "</add>"
    return solr_docs


def parse_file(file_path):
    # filename = os.path.basename(file_path)

    try:
        if isinstance(file_path, bytes):
            file_path = io.BytesIO(file_path)

        # Load the XML file
        tree = etree.parse(file_path)
        # print(tree)
        # print(f'Parsed: {filename}')

        # checks for sampled data:
        # check 1: based on content tier - if 0 do not include
        # check 2: based on translations - if english include, if not english then include only if translated

        content_tier, metadata_tier = find_tier_information(tree, namespaces)
        europeana_id = find_single_element_text(tree, './/ore:proxyIn')

        isTranslated = check_if_translated(europeana_id)

        if not isTranslated:
            # print("IS NOT TRANSLATED")
            language = find_single_element_text(tree, './/edm:EuropeanaAggregation/edm:language')
            # print(language)
            if language != 'en':
                # print(f"SKIPPING")
                return None
        else:
            # print("is translated")
            pass

        if content_tier == 0:
            # print(f"SKIPPING")
            return None
        else:
            # print("content is fine")
            pass

        europeana_id = '/'.join(europeana_id.rsplit('/', 2)[-2:])
        europeana_id = '/'+europeana_id

        data = {
            'europeana_id': europeana_id,
            'dcterms:modified': find_single_element_text(tree, './/dcterms:modified'),
            'edm:type': find_single_element_text(tree, './/edm:type'),
            'contentTier': content_tier, 
            'metadataTier': metadata_tier,
            "provided_data": {
                'edm:dataProvider': find_multiple_elements_text(tree, './/ore:Aggregation/edm:dataProvider'),
                'edm:intermediateProvider': find_multiple_elements_text(tree, './/ore:Aggregation/edm:intemediateProvider'),
                'edm:provider': find_multiple_elements_text(tree, './/ore:Aggregation/edm:provider'),
                'dc:contributor': find_with_condition("/provider", ".//dc:contributor", tree, namespaces),
                'dc:coverage': find_with_condition("/provider", ".//dc:coverage", tree, namespaces),
                'dc:creator': find_with_condition("/provider", ".//dc:creator", tree, namespaces),
                'dc:date': find_with_condition("/provider", ".//dc:date", tree, namespaces),
                'dc:description': find_with_condition("/provider", ".//dc:description", tree, namespaces),
                'dc:format': find_with_condition("/provider", ".//dc:format", tree, namespaces),
                'dc:language': find_with_condition("/provider", ".//dc:language", tree, namespaces),
                'dc:publisher': find_with_condition("/provider", ".//dc:publisher", tree, namespaces),
                'dc:source': find_with_condition("/provider", ".//dc:source", tree, namespaces),
                'dc:subject': find_with_condition("/provider", ".//dc:subject", tree, namespaces),
                'dc:title': find_with_condition("/provider", ".//dc:title", tree, namespaces),
                'dc:type': find_with_condition("/provider", ".//dc:type", tree, namespaces),
                'dcterms:alternative': find_with_condition("/provider", ".//dcterms:alternative", tree, namespaces),
                'dcterms:created': find_with_condition("/provider", ".//dcterms:created", tree, namespaces),
                'dcterms:issued': find_with_condition("/provider", ".//dcterms:issued", tree, namespaces),
                'dcterms:medium': find_with_condition("/provider", ".//dcterms:medium", tree, namespaces),
                'dcterms:provenance': find_with_condition("/provider", ".//dcterms:provenance", tree, namespaces),
                'dcterms:spatial': find_with_condition("/provider", ".//dcterms:spatial", tree, namespaces),
                'dcterms:temporal': find_with_condition("/provider", ".//dcterms:temporal", tree, namespaces),
                'edm:currentLocation': find_with_condition("/provider", ".//edm:currentLocation", tree, namespaces),
            },
            "enriched_data": {
                "dc:contributor": find_with_condition("/europeana", ".//dc:contributor", tree, namespaces),
                "dc:coverage": find_with_condition("/europeana", ".//dc:coverage", tree, namespaces),
                "dc:creator": find_with_condition("/europeana", ".//dc:creator", tree, namespaces),
                "dc:date": find_with_condition("/europeana", ".//dc:date", tree, namespaces),
                "dc:description": find_with_condition("/europeana", ".//dc:description", tree, namespaces),
                "dc:format": find_with_condition("/europeana", ".//dc:format", tree, namespaces),
                'dc:language': find_with_condition("/europeana", ".//dc:language", tree, namespaces),
                'dc:publisher': find_with_condition("/europeana", ".//dc:publisher", tree, namespaces),
                'dc:source': find_with_condition("/europeana", ".//dc:source", tree, namespaces),
                'dc:subject': find_with_condition("/europeana", ".//dc:subject", tree, namespaces),
                'dc:title': find_with_condition("/europeana", ".//dc:title", tree, namespaces),
                'dc:type': find_with_condition("/europeana", ".//dc:type", tree, namespaces),
                'dcterms:alternative': find_with_condition("/europeana", ".//dcterms:alternative", tree, namespaces),
                'dcterms:created': find_with_condition("/europeana", ".//dcterms:created", tree, namespaces),
                'dcterms:issued': find_with_condition("/europeana", ".//dcterms:issued", tree, namespaces),
                'dcterms:medium': find_with_condition("/europeana", ".//dcterms:medium", tree, namespaces),
                'dcterms:provenance': find_with_condition("/europeana", ".//dcterms:provenance", tree, namespaces),
                'dcterms:spatial': find_with_condition("/europeana", ".//dcterms:spatial", tree, namespaces),
                'dcterms:temporal': find_with_condition("/europeana", ".//dcterms:temporal", tree, namespaces),
                'edm:currentLocation': find_with_condition("/europeana", ".//edm:currentLocation", tree, namespaces),
            },
            "translated_data":{
                "dc:contributor": find_with_condition("/europeana", ".//dc:contributor", tree, namespaces, lang='en'),
                "dc:coverage": find_with_condition("/europeana", ".//dc:coverage", tree, namespaces, lang='en'),
                "dc:creator": find_with_condition("/europeana", ".//dc:creator", tree, namespaces, lang='en'),
                "dc:date": find_with_condition("/europeana", ".//dc:date", tree, namespaces, lang='en'),
                "dc:description": find_with_condition("/europeana", ".//dc:description", tree, namespaces, lang='en'),
                "dc:format": find_with_condition("/europeana", ".//dc:format", tree, namespaces, lang='en'),
                'dc:language': find_with_condition("/europeana", ".//dc:language", tree, namespaces, lang='en'),
                'dc:publisher': find_with_condition("/europeana", ".//dc:publisher", tree, namespaces, lang='en'),
                'dc:source': find_with_condition("/europeana", ".//dc:source", tree, namespaces, lang='en'),
                'dc:subject': find_with_condition("/europeana", ".//dc:subject", tree, namespaces, lang='en'),
                'dc:title': find_with_condition("/europeana", ".//dc:title", tree, namespaces, lang='en'),
                'dc:type': find_with_condition("/europeana", ".//dc:type", tree, namespaces, lang='en'),
                'dcterms:alternative': find_with_condition("/europeana", ".//dcterms:alternative", tree, namespaces, lang='en'),
                'dcterms:created': find_with_condition("/europeana", ".//dcterms:created", tree, namespaces, lang='en'),
                'dcterms:issued': find_with_condition("/europeana", ".//dcterms:issued", tree, namespaces, lang='en'),
                'dcterms:medium': find_with_condition("/europeana", ".//dcterms:medium", tree, namespaces, lang='en'),
                'dcterms:provenance': find_with_condition("/europeana", ".//dcterms:provenance", tree, namespaces, lang='en'),
                'dcterms:spatial': find_with_condition("/europeana", ".//dcterms:spatial", tree, namespaces, lang='en'),
                'dcterms:temporal': find_with_condition("/europeana", ".//dcterms:temporal", tree, namespaces, lang='en'),
                'edm:currentLocation': find_with_condition("/europeana", ".//edm:currentLocation", tree, namespaces, lang='en'),
            }
        }

        solr_doc_alt = generate_solr_xml(data)
        
    except Exception as e:
        print(f"Failed to parse {file_path}: {e}")
    
    return solr_doc_alt

def write_data(data, output_directory):
    # Ensure the output directory exists
    os.makedirs(output_directory)
    
    # Initialize a counter for file names
    doc_counter = 1

    # Iterate over each XML document in the data list
    for xml_doc in data:
        # Define the output file name
        output_file = os.path.join(output_directory, f"{doc_counter}.xml")

        # Write the data to the output file
        with open(output_file, 'w') as file:
            if xml_doc is not None:
                file.write(xml_doc)
        
        # print(f"Data written to {output_file}")

        # Increment the counter for the next file
        doc_counter += 1

def remove_duplicates(xml_data):
    # Parse the XML data
    root = ET.fromstring(xml_data)

    # Initialize a set to track unique europeana_id
    seen_ids = set()
    unique_docs = []

    # Iterate over each document and filter out duplicates
    for doc in root.findall(".//doc"):
        europeana_id = doc.find(".//field[@name='europeana_id']").text
        if europeana_id not in seen_ids:
            seen_ids.add(europeana_id)
            unique_docs.append(doc)

    # Build a new XML tree with unique documents
    new_root = ET.Element("add")
    for doc in unique_docs:
        new_root.append(doc)

    # Convert the tree back to a string
    new_xml_data = ET.tostring(new_root, encoding='unicode')
    return new_xml_data

def remove_none(xml_doc):
    # Parse the XML document using lxml
    root = ET.fromstring(xml_doc)

    # Iterate over all <doc> elements
    for doc in root.xpath(".//doc"):
        # Find all <field> elements within each <doc>
        fields = doc.xpath(".//field")
        
        # Iterate through each field and remove it if its text is None or empty
        for field in fields:
            if field.text is None or field.text.strip() == "None":
                field.getparent().remove(field)  # Remove the field if it has a None or empty value

    # Convert the modified XML tree back to a string
    cleaned_xml_data = ET.tostring(root, pretty_print=True, encoding='unicode')
    return cleaned_xml_data
