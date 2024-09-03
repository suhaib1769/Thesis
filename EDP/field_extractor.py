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
        if element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource'):
            return element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
        else:
            return element.text
    return None

def find_multiple_elements_text(tree, xpath_query):
    elements = tree.findall(xpath_query, namespaces)
    return [element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource') or element.text 
            for element in elements if element is not None and xpath_query != '//dc:date']

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

# def find_with_condition(condition, search, filename, tree, namespaces, lang=None):
#     # Find all <ore:Proxy> elements with rdf:about containing the condition
#     paths = tree.xpath(f"//ore:Proxy[contains(@rdf:about, '{condition}')]", namespaces=namespaces)
    
#     # Check if we found the <ore:Proxy> elements
#     if paths:
#         for path in paths:
#             # Build the XPath query with an optional language filter
#             if lang:
#                 elements = path.xpath(f"{search}[@xml:lang='{lang}']", namespaces=namespaces)
#             else:
#                 elements = path.xpath(f"{search}", namespaces=namespaces)
#                 # Check if any of these elements have lang='en'
#                 en_elements = path.xpath(f"{search}[@xml:lang='en']", namespaces=namespaces)
#                 if en_elements:
#                     return None  # Return None if any elements with lang='en' are found
            
#             if elements:
#                 for element in elements:
#                     # Return the text content of the element if found
#                     return element.text
#             else:
#                 # No elements found with the specified search and language
#                 return None
#     else:
#         print(f'No matching ore:Proxy element found in {filename}')
#         return None

def find_with_condition(condition, search, filename, tree, namespaces, lang=None):
    # Find all <ore:Proxy> elements with rdf:about containing the condition
    paths = tree.xpath(f"//ore:Proxy[contains(@rdf:about, '{condition}')]", namespaces=namespaces)
    
    # Check if we found the <ore:Proxy> elements
    if paths:
        for path in paths:
            # Build the XPath query with an optional language filter
            if lang:
                elements = path.xpath(f"{search}[@xml:lang='{lang}']", namespaces=namespaces)
            else:
                elements = path.xpath(f"{search}", namespaces=namespaces)
                # Check if any of these elements have lang='en'
                en_elements = path.xpath(f"{search}[@xml:lang='en']", namespaces=namespaces)
                if en_elements:
                    return None  # Return None if any elements with lang='en' are found
            
            if elements:
                for element in elements:
                    # Check if the element has a reference to a resource
                    resource_ref = element.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
                    if resource_ref:
                        # Find the resource in skos:Concept, edm:Agent, edm:TimeSpan, or edm:Place
                        resource_element = tree.xpath(
                            f"//skos:Concept[@rdf:about='{resource_ref}'] | "
                            f"//edm:Agent[@rdf:about='{resource_ref}'] | "
                            f"//edm:TimeSpan[@rdf:about='{resource_ref}'] | "
                            f"//edm:Place[@rdf:about='{resource_ref}']",
                            namespaces=namespaces
                        )
                        
                        if resource_element:
                            # Get the skos:prefLabel and skos:altLabel from the resource element
                            pref_label = resource_element[0].xpath("skos:prefLabel/text()", namespaces=namespaces)
                            alt_label = resource_element[0].xpath("skos:altLabel/text()", namespaces=namespaces)
                            
                            # Combine prefLabel and altLabel if available, otherwise return the element text
                            combined_labels = ', '.join(pref_label + alt_label)
                            if combined_labels:
                                return combined_labels

                    # Return the text content of the element if no resource reference or labels are found
                    return element.text

            else:
                # No elements found with the specified search and language
                return None
    else:
        print(f'No matching ore:Proxy element found in {filename}')
        return None
    

def check_if_translated(europeana_id, subdirectory):
    try:
        # Extract the last part of the europeana_id
        last_part = europeana_id.split('/')[-1]
        
        # Construct the file path for the translation CSV
        translation_subdirectory = subdirectory + '.csv'
        csv_path = f'/home/sbasir/Thesis/Thesis/EDP/sample_data/translations/{translation_subdirectory}'
        
        # Check if the CSV file exists
        if not os.path.exists(csv_path):
            # Return False if the file does not exist
            print("does not exist")
            return False
        
        # Load the CSV file
        translation_csv = pd.read_csv(csv_path)
        
        # Check if the last_part is in the 'item_id' column of the DataFrame
        translated = last_part in translation_csv['item_id'].values
        
        # Return True if found, False otherwise
        return translated, last_part

    except FileNotFoundError:
        # If the file is not found, print an error message and return False
        print(f"File not found: {csv_path}")
        return False, last_part

    except Exception as e:
        # Catch all other exceptions, print an error message, and return False
        print(f"Error checking translation for {europeana_id}: {e}")
        return False, last_part

def parse_rdf_files(directory, subdirectory):

    docs = []

    ## TODO: IMPLEMENT THE CODE FOR LOOKING INTO THE RDF:RESOURCE ATTRIBUTE

    # Get all files in the directory that end with '.rdf' or '.xml'
    all_files = [filename for filename in os.listdir(directory) if filename.endswith('.rdf') or filename.endswith('.xml')]

    percentage = 1
    
    # Calculate the number of files to sample (10% of total)
    sample_size = max(1, int(len(all_files) * percentage))  # Ensure at least one file is selected if len(all_files) < 10

    # Randomly sample 10% of the files
    sampled_files = random.sample(all_files, sample_size)

    # Iterate over each file in the directory
    for filename in sampled_files:
        # print(filename)
        file_path = os.path.join(directory, filename)
        
        try:
            # Load the XML file
            tree = etree.parse(file_path)
            # print(f'Parsed: {filename}')

            # checks for sampled data:
            # check 1: based on content tier - if 0 do not include
            # check 2: based on translations - if english include, it not english include if translated

            content_tier, metadata_tier = find_tier_information(tree, namespaces)
            europeana_id = find_single_element_text(tree, '//ore:proxyIn')

            isTranslated, europeana_id = check_if_translated(europeana_id, subdirectory)
            if not isTranslated:
                print("IS NOT TRANSLATED")
                language = find_single_element_text(tree, '//edm:EuropeanaAggregation/edm:language')
                print(language)
                if language != 'en':
                    print("SKIPPING")
                    continue
            else:
                print("is translated")

            if content_tier == 0:
                print("SKIPPING")
                continue
            else:
                print("content is fine")
            
            print("passed checks")
            # extract data
            data = {
                'dcterms:modified': find_single_element_text(tree, '//dcterms:modified'),
                'edm:type': find_single_element_text(tree, '//edm:type'),
                "provided_data": {
                    'edm:dataProvider': find_single_element_text(tree, '//ore:Aggregation/edm:dataProvider'),
                    'edm:intermediateProvider': find_single_element_text(tree, '//ore:Aggregation/edm:intemediateProvider'),
                    'edm:provider': find_single_element_text(tree, '//ore:Aggregation/edm:provider'),
                    'dc:contributor': find_with_condition("/provider", ".//dc:contributor", filename, tree, namespaces),
                    'dc:coverage': find_with_condition("/provider", ".//dc:coverage", filename, tree, namespaces),
                    'dc:creator': find_with_condition("/provider", ".//dc:creator", filename, tree, namespaces),
                    'dc:date': find_with_condition("/provider", ".//dc:date", filename, tree, namespaces),
                    'dc:description': find_with_condition("/provider", ".//dc:description", filename, tree, namespaces),
                    'dc:format': find_with_condition("/provider", ".//dc:format", filename, tree, namespaces),
                    'dc:language': find_with_condition("/provider", ".//dc:language", filename, tree, namespaces),
                    'dc:publisher': find_with_condition("/provider", ".//dc:publisher", filename, tree, namespaces),
                    'dc:source': find_with_condition("/provider", ".//dc:source", filename, tree, namespaces),
                    'dc:subject': find_with_condition("/provider", ".//dc:subject", filename, tree, namespaces),
                    'dc:title': find_with_condition("/provider", ".//dc:title", filename, tree, namespaces),
                    'dc:type': find_with_condition("/provider", ".//dc:type", filename, tree, namespaces),
                    'dcterms:alternative': find_with_condition("/provider", ".//dcterms:alternative", filename, tree, namespaces),
                    'dcterms:created': find_with_condition("/provider", ".//dcterms:created", filename, tree, namespaces),
                    'dcterms:issued': find_with_condition("/provider", ".//dcterms:issued", filename, tree, namespaces),
                    'dcterms:medium': find_with_condition("/provider", ".//dcterms:medium", filename, tree, namespaces),
                    'dcterms:provenance': find_with_condition("/provider", ".//dcterms:provenance", filename, tree, namespaces),
                    'dcterms:spatial': find_with_condition("/provider", ".//dcterms:spatial", filename, tree, namespaces),
                    'dcterms:temporal': find_with_condition("/provider", ".//dcterms:temporal", filename, tree, namespaces),
                    'edm:currentLocation': find_with_condition("/provider", ".//edm:currentLocation", filename, tree, namespaces),
                },
                "enriched_data": {
                    "dc:contributor": find_with_condition("/europeana", ".//dc:contributor", filename, tree, namespaces),
                    "dc:coverage": find_with_condition("/europeana", ".//dc:coverage", filename, tree, namespaces),
                    "dc:creator": find_with_condition("/europeana", ".//dc:creator", filename, tree, namespaces),
                    "dc:date": find_with_condition("/europeana", ".//dc:date", filename, tree, namespaces),
                    "dc:description": find_with_condition("/europeana", ".//dc:description", filename, tree, namespaces),
                    "dc:format": find_with_condition("/europeana", ".//dc:format", filename, tree, namespaces),
                    'dc:language': find_with_condition("/europeana", ".//dc:language", filename, tree, namespaces),
                    'dc:publisher': find_with_condition("/europeana", ".//dc:publisher", filename, tree, namespaces),
                    'dc:source': find_with_condition("/europeana", ".//dc:source", filename, tree, namespaces),
                    'dc:subject': find_with_condition("/europeana", ".//dc:subject", filename, tree, namespaces),
                    'dc:title': find_with_condition("/europeana", ".//dc:title", filename, tree, namespaces),
                    'dc:type': find_with_condition("/europeana", ".//dc:type", filename, tree, namespaces),
                    'dcterms:alternative': find_with_condition("/europeana", ".//dcterms:alternative", filename, tree, namespaces),
                    'dcterms:created': find_with_condition("/europeana", ".//dcterms:created", filename, tree, namespaces),
                    'dcterms:issued': find_with_condition("/europeana", ".//dcterms:issued", filename, tree, namespaces),
                    'dcterms:medium': find_with_condition("/europeana", ".//dcterms:medium", filename, tree, namespaces),
                    'dcterms:provenance': find_with_condition("/europeana", ".//dcterms:provenance", filename, tree, namespaces),
                    'dcterms:spatial': find_with_condition("/europeana", ".//dcterms:spatial", filename, tree, namespaces),
                    'dcterms:temporal': find_with_condition("/europeana", ".//dcterms:temporal", filename, tree, namespaces),
                    'edm:currentLocation': find_with_condition("/europeana", ".//edm:currentLocation", filename, tree, namespaces),
                },
                "translated_data":{
                    "dc:contributor": find_with_condition("/europeana", ".//dc:contributor", filename, tree, namespaces, lang='en'),
                    "dc:coverage": find_with_condition("/europeana", ".//dc:coverage", filename, tree, namespaces, lang='en'),
                    "dc:creator": find_with_condition("/europeana", ".//dc:creator", filename, tree, namespaces, lang='en'),
                    "dc:date": find_with_condition("/europeana", ".//dc:date", filename, tree, namespaces, lang='en'),
                    "dc:description": find_with_condition("/europeana", ".//dc:description", filename, tree, namespaces, lang='en'),
                    "dc:format": find_with_condition("/europeana", ".//dc:format", filename, tree, namespaces, lang='en'),
                    'dc:language': find_with_condition("/europeana", ".//dc:language", filename, tree, namespaces, lang='en'),
                    'dc:publisher': find_with_condition("/europeana", ".//dc:publisher", filename, tree, namespaces, lang='en'),
                    'dc:source': find_with_condition("/europeana", ".//dc:source", filename, tree, namespaces, lang='en'),
                    'dc:subject': find_with_condition("/europeana", ".//dc:subject", filename, tree, namespaces, lang='en'),
                    'dc:title': find_with_condition("/europeana", ".//dc:title", filename, tree, namespaces, lang='en'),
                    'dc:type': find_with_condition("/europeana", ".//dc:type", filename, tree, namespaces, lang='en'),
                    'dcterms:alternative': find_with_condition("/europeana", ".//dcterms:alternative", filename, tree, namespaces, lang='en'),
                    'dcterms:created': find_with_condition("/europeana", ".//dcterms:created", filename, tree, namespaces, lang='en'),
                    'dcterms:issued': find_with_condition("/europeana", ".//dcterms:issued", filename, tree, namespaces, lang='en'),
                    'dcterms:medium': find_with_condition("/europeana", ".//dcterms:medium", filename, tree, namespaces, lang='en'),
                    'dcterms:provenance': find_with_condition("/europeana", ".//dcterms:provenance", filename, tree, namespaces, lang='en'),
                    'dcterms:spatial': find_with_condition("/europeana", ".//dcterms:spatial", filename, tree, namespaces, lang='en'),
                    'dcterms:temporal': find_with_condition("/europeana", ".//dcterms:temporal", filename, tree, namespaces, lang='en'),
                    'edm:currentLocation': find_with_condition("/europeana", ".//edm:currentLocation", filename, tree, namespaces, lang='en'),
                }
            }

            solr_docs = "<add>"
            # Build Solr document
            solr_docs += f"""
            <doc>
                <field name="europeana_id">{europeana_id}</field>
                <field name="timestamp_update">{data['dcterms:modified']}</field>
                <field name="edm_type">{data['edm:type']}</field>
                <field name="content_tier">{content_tier}</field>
                <field name="metadata_tier">{metadata_tier}</field>
                <provided_data>
                    <field name="data_provider">{data['provided_data']['edm:dataProvider']}</field>
                    <field name="intermediate_provider">{data['provided_data']['edm:intermediateProvider']}</field>
                    <field name="provider">{data['provided_data']['edm:provider']}</field>
                    <field name="dc_contributor">{data['provided_data']['dc:contributor']}</field>
                    <field name="dc_coverage">{data['provided_data']['dc:coverage']}</field>
                    <field name="dc_creator">{data['provided_data']['dc:creator']}</field>
                    <field name="dc_date">{data['provided_data']['dc:date']}</field>
                    <field name="dc_description">{data['provided_data']['dc:description']}</field>
                    <field name="dc_format">{data['provided_data']['dc:format']}</field>
                    <field name="dc_language">{data['provided_data']['dc:language']}</field>
                    <field name="dc_publisher">{data['provided_data']['dc:publisher']}</field>
                    <field name="dc_source">{data['provided_data']['dc:source']}</field>
                    <field name="dc_subject">{data['provided_data']['dc:subject']}</field>
                    <field name="dc_title">{data['provided_data']['dc:title']}</field>
                    <field name="dc_type">{data['provided_data']['dc:type']}</field>
                    <field name="dcterms_alternative">{data['provided_data']['dcterms:alternative']}</field>
                    <field name="dcterms_created">{data['provided_data']['dcterms:created']}</field>
                    <field name="dcterms_issued">{data['provided_data']['dcterms:issued']}</field>
                    <field name="dcterms_medium">{data['provided_data']['dcterms:medium']}</field>
                    <field name="dcterms_provenance">{data['provided_data']['dcterms:provenance']}</field>
                    <field name="dcterms_spatial">{data['provided_data']['dcterms:spatial']}</field>
                    <field name="dcterms_temporal">{data['provided_data']['dcterms:temporal']}</field>
                    <field name="edm_currentLocation">{data['provided_data']['edm:currentLocation']}</field>
                </provided_data>
                <enriched_data>
                    <field name="dc_contributor">{data['enriched_data']['dc:contributor']}</field>
                    <field name="dc_coverage">{data['enriched_data']['dc:coverage']}</field>
                    <field name="dc_creator">{data['enriched_data']['dc:creator']}</field>
                    <field name="dc_date">{data['enriched_data']['dc:date']}</field>
                    <field name="dc_description">{data['enriched_data']['dc:description']}</field>
                    <field name="dc_format">{data['enriched_data']['dc:format']}</field>
                    <field name="dc_language">{data['enriched_data']['dc:language']}</field>
                    <field name="dc_publisher">{data['enriched_data']['dc:publisher']}</field>
                    <field name="dc_source">{data['enriched_data']['dc:source']}</field>
                    <field name="dc_subject">{data['enriched_data']['dc:subject']}</field>
                    <field name="dc_title">{data['enriched_data']['dc:title']}</field>
                    <field name="dc_type">{data['enriched_data']['dc:type']}</field>
                    <field name="dcterms_alternative">{data['enriched_data']['dcterms:alternative']}</field>
                    <field name="dcterms_created">{data['enriched_data']['dcterms:created']}</field>
                    <field name="dcterms_issued">{data['enriched_data']['dcterms:issued']}</field>
                    <field name="dcterms_medium">{data['enriched_data']['dcterms:medium']}</field>
                    <field name="dcterms_provenance">{data['enriched_data']['dcterms:provenance']}</field>
                    <field name="dcterms_spatial">{data['enriched_data']['dcterms:spatial']}</field>
                    <field name="dcterms_temporal">{data['enriched_data']['dcterms:temporal']}</field>
                    <field name="edm_currentLocation">{data['enriched_data']['edm:currentLocation']}</field>
                </enriched_data>
                <translated_data>
                        <field name="dc_contributor">{data['translated_data']['dc:contributor']}</field>
                    <field name="dc_coverage">{data['translated_data']['dc:coverage']}</field>
                    <field name="dc_creator">{data['translated_data']['dc:creator']}</field>
                    <field name="dc_date">{data['translated_data']['dc:date']}</field>
                    <field name="dc_description">{data['translated_data']['dc:description']}</field>
                    <field name="dc_format">{data['translated_data']['dc:format']}</field>
                    <field name="dc_language">{data['translated_data']['dc:language']}</field>
                    <field name="dc_publisher">{data['translated_data']['dc:publisher']}</field>
                    <field name="dc_source">{data['translated_data']['dc:source']}</field>
                    <field name="dc_subject">{data['translated_data']['dc:subject']}</field>
                    <field name="dc_title">{data['translated_data']['dc:title']}</field>
                    <field name="dc_type">{data['translated_data']['dc:type']}</field>
                    <field name="dcterms_alternative">{data['translated_data']['dcterms:alternative']}</field>
                    <field name="dcterms_created">{data['translated_data']['dcterms:created']}</field>
                    <field name="dcterms_issued">{data['translated_data']['dcterms:issued']}</field>
                    <field name="dcterms_medium">{data['translated_data']['dcterms:medium']}</field>
                    <field name="dcterms_provenance">{data['translated_data']['dcterms:provenance']}</field>
                    <field name="dcterms_spatial">{data['translated_data']['dcterms:spatial']}</field>
                    <field name="dcterms_temporal">{data['translated_data']['dcterms:temporal']}</field>
                    <field name="edm_currentLocation">{data['translated_data']['edm:currentLocation']}</field>
                </translated_data>
            </doc>
            """
            solr_docs += "</add>"
            docs.append(solr_docs)
            
        except Exception as e:
            print(f"Failed to parse {filename}: {e}")
    
    # # Close the Solr document
    # solr_docs += "</add>"
    # docs.append(solr_docs)
    
    # Return the compiled Solr XML document
    return docs

def write_data(data, output_directory):
    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)
    
    # Initialize a counter for file names
    doc_counter = 1

    # Iterate over each XML document in the data list
    for xml_doc in data:
        # Define the output file name
        output_file = os.path.join(output_directory, f"{doc_counter}.xml")

        # Write the data to the output file
        with open(output_file, 'w') as file:
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