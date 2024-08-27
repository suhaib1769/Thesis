import rdflib
import os
from rdflib.namespace import RDF, DC, Namespace
import xml.etree.ElementTree as ET

def parse_rdf_files(directory):
    # Define namespaces
    ORE = Namespace("http://www.openarchives.org/ore/terms/")
    EDM = Namespace("http://www.europeana.eu/schemas/edm/")
    DCTERMS = Namespace("http://purl.org/dc/terms/")
    SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
    FOAF = Namespace("http://xmlns.com/foaf/0.1/")

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
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX edm: <http://www.europeana.eu/schemas/edm/>
            PREFIX ore: <http://www.openarchives.org/ore/terms/>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            
            SELECT ?title ?creator ?date ?id ?dataProvider ?intermediateProvider ?provider ?contributor ?coverage ?description ?format ?language ?publisher ?source ?subject ?type ?alternative ?created ?issued ?medium ?provenance ?spatial ?temporal ?currentLocation ?edmType ?agentLabel ?agentAltLabel ?agentName ?timespanLabel ?timespanAltLabel ?placeLabel ?placeAltLabel ?conceptLabel ?conceptAltLabel
            WHERE {
                ?s dc:title ?title .
                OPTIONAL { ?s dc:creator ?creator . }
                OPTIONAL { ?s dc:date ?date . }
                ?proxy ore:proxyIn ?id .
                FILTER (lang(?title) = 'en-GB')

                OPTIONAL { ?s edm:dataProvider ?dataProvider . }
                OPTIONAL { ?s edm:intermediateProvider ?intermediateProvider . }
                OPTIONAL { ?s edm:provider ?provider . }
                OPTIONAL { ?s dc:contributor ?contributor . }
                OPTIONAL { ?s dc:coverage ?coverage . }
                OPTIONAL { ?s dc:description ?description . }
                OPTIONAL { ?s dc:format ?format . }
                OPTIONAL { ?s dc:language ?language . }
                OPTIONAL { ?s dc:publisher ?publisher . }
                OPTIONAL { ?s dc:source ?source . }
                OPTIONAL { ?s dc:subject ?subject . }
                OPTIONAL { ?s dc:type ?type . }
                OPTIONAL { ?s dcterms:alternative ?alternative . }
                OPTIONAL { ?s dcterms:created ?created . }
                OPTIONAL { ?s dcterms:issued ?issued . }
                OPTIONAL { ?s dcterms:medium ?medium . }
                OPTIONAL { ?s dcterms:provenance ?provenance . }
                OPTIONAL { ?s dcterms:spatial ?spatial . }
                OPTIONAL { ?s dcterms:temporal ?temporal . }
                OPTIONAL { ?s edm:currentLocation ?currentLocation . }
                OPTIONAL { ?s edm:type ?edmType . }
                OPTIONAL { ?agent skos:prefLabel ?agentLabel . }
                OPTIONAL { ?agent skos:altLabel ?agentAltLabel . }
                OPTIONAL { ?agent foaf:name ?agentName . }
                OPTIONAL { ?timespan skos:prefLabel ?timespanLabel . }
                OPTIONAL { ?timespan skos:altLabel ?timespanAltLabel . }
                OPTIONAL { ?place skos:prefLabel ?placeLabel . }
                OPTIONAL { ?place skos:altLabel ?placeAltLabel . }
                OPTIONAL { ?concept skos:prefLabel ?conceptLabel . }
                OPTIONAL { ?concept skos:altLabel ?conceptAltLabel . }
            }
            """
            
            results = g.query(query)
            
            # Append results to the Solr document string
            for row in results:
                def safe_str(val):
                    return str(val) if val else ""
                
                title = safe_str(row.title)
                creator = safe_str(row.creator)
                date = safe_str(row.date)
                id = "/2021672" + safe_str(row.id).split("/2021672")[1] if row.id else ""

                # Additional fields
                dataProvider = safe_str(row.dataProvider)
                intermediateProvider = safe_str(row.intermediateProvider)
                provider = safe_str(row.provider)
                contributor = safe_str(row.contributor)
                coverage = safe_str(row.coverage)
                description = safe_str(row.description)
                format_ = safe_str(row.format)
                language = safe_str(row.language)
                publisher = safe_str(row.publisher)
                source = safe_str(row.source)
                subject = safe_str(row.subject)
                type_ = safe_str(row.type)
                alternative = safe_str(row.alternative)
                created = safe_str(row.created)
                issued = safe_str(row.issued)
                medium = safe_str(row.medium)
                provenance = safe_str(row.provenance)
                spatial = safe_str(row.spatial)
                temporal = safe_str(row.temporal)
                currentLocation = safe_str(row.currentLocation)
                edmType = safe_str(row.edmType)
                agentLabel = safe_str(row.agentLabel)
                agentAltLabel = safe_str(row.agentAltLabel)
                agentName = safe_str(row.agentName)
                timespanLabel = safe_str(row.timespanLabel)
                timespanAltLabel = safe_str(row.timespanAltLabel)
                placeLabel = safe_str(row.placeLabel)
                placeAltLabel = safe_str(row.placeAltLabel)
                conceptLabel = safe_str(row.conceptLabel)
                conceptAltLabel = safe_str(row.conceptAltLabel)

                solr_docs += f"""
                <doc>
                    <field name="europeana_id">{id}</field>
                    <field name="proxy_dc_title">{title}</field>
                    <field name="proxy_dc_creator">{creator}</field>
                    <field name="proxy_dc_date">{date}</field>
                    <field name="edm_dataProvider">{dataProvider}</field>
                    <field name="edm_intermediateProvider">{intermediateProvider}</field>
                    <field name="edm_provider">{provider}</field>
                    <field name="proxy_dc_contributor">{contributor}</field>
                    <field name="proxy_dc_coverage">{coverage}</field>
                    <field name="proxy_dc_description">{description}</field>
                    <field name="proxy_dc_format">{format_}</field>
                    <field name="proxy_dc_language">{language}</field>
                    <field name="proxy_dc_publisher">{publisher}</field>
                    <field name="proxy_dc_source">{source}</field>
                    <field name="proxy_dc_subject">{subject}</field>
                    <field name="proxy_dc_type">{type_}</field>
                    <field name="dcterms_alternative">{alternative}</field>
                    <field name="dcterms_created">{created}</field>
                    <field name="dcterms_issued">{issued}</field>
                    <field name="dcterms_medium">{medium}</field>
                    <field name="dcterms_provenance">{provenance}</field>
                    <field name="dcterms_spatial">{spatial}</field>
                    <field name="dcterms_temporal">{temporal}</field>
                    <field name="edm_currentLocation">{currentLocation}</field>
                    <field name="edm_type">{edmType}</field>
                    <field name="agent_skos_prefLabel">{agentLabel}</field>
                    <field name="agent_skos_altLabel">{agentAltLabel}</field>
                    <field name="agent_foaf_name">{agentName}</field>
                    <field name="timespan_skos_prefLabel">{timespanLabel}</field>
                    <field name="timespan_skos_altLabel">{timespanAltLabel}</field>
                    <field name="place_skos_prefLabel">{placeLabel}</field>
                    <field name="place_skos_altLabel">{placeAltLabel}</field>
                    <field name="concept_skos_prefLabel">{conceptLabel}</field>
                    <field name="concept_skos_altLabel">{conceptAltLabel}</field>
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
directory = '/home/sbasir/Thesis/Thesis/EDP/test'  # Change this to your directory containing RDF/XML files
output_file = '/home/sbasir/Thesis/Thesis/EDP/cleaned.xml'
solr_xml_data = parse_rdf_files(directory)
solr_xml_data_cleaned = remove_duplicates(solr_xml_data)
write_solr_xml(solr_xml_data_cleaned, output_file)