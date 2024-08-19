import rdflib
import os
from rdflib.namespace import RDF, DC, Namespace
import xml.etree.ElementTree as ET

def parse_rdf_files(directory):
    # Define namespaces
    ORE = Namespace("http://www.openarchives.org/ore/terms/")

    # Start building the Solr input document
    solr_docs = "<add>"
    
    # Iterate over each file in the directory
    for filename in os.listdir(directory):
        if filename.endswith('.rdf') or filename.endswith('.xml'):
            file_path = os.path.join(directory, filename)
            
            # Load RDF/XML data
            g = rdflib.Graph()
            try:
                g.parse(file_path, format='xml')
            except Exception as e:
                print(f"Failed to parse {filename}: {e}")
                continue
            
            # SPARQL query to extract required fields and ID
            query = """
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX ore: <http://www.openarchives.org/ore/terms/>
            SELECT ?title ?creator ?date ?id WHERE {
                ?s dc:title ?title .
                OPTIONAL {?s dc:creator ?creator .}
                OPTIONAL {?s dc:date ?date .}
                ?proxy ore:proxyIn ?id .
                FILTER (lang(?title) = 'en-GB')
            }
            """
            
            results = g.query(query)
            
            # Append results to the Solr document string
            for row in results:
                title = str(row.title) if row.title else ""
                creator = str(row.creator) if row.creator else ""
                date = str(row.date) if row.date else ""
                # remove everything before "/2021672"
                id = str(row.id).split("/2021672")[1] if row.id else ""
                # append /2021672 to the id
                id = "/2021672" + id
                
                solr_docs += f"""
                <doc>
                    <field name="europeana_id">{id}</field>
                    <field name="proxy_dc_title">{title}</field>
                    <field name="proxy_dc_creator">{creator}</field>
                    <field name="proxy_dc_date">{date}</field>
                </doc>
                """

    # Close the Solr document
    solr_docs += "</add>"
    
    # Return the compiled Solr XML document
    return solr_docs

def write_solr_xml(data, output_file):
    # Write the data to an XML file
    with open(output_file, 'w') as file:
        file.write(data)
    print(f"Data written to {output_file}")


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

# Usage
directory = 'Thesis/EDP/2021672'  # Change this to your directory containing RDF/XML files
output_file = 'Thesis/EDP/output_solr34.xml'
solr_xml_data = parse_rdf_files(directory)
solr_xml_data_cleaned = remove_duplicates(solr_xml_data)
write_solr_xml(solr_xml_data_cleaned, output_file)
