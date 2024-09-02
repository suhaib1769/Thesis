import xml.etree.ElementTree as ET
import pandas as pd

class Parser2:

    # Function to clean text by replacing non-breaking spaces with regular spaces
    @staticmethod
    def clean_text(text):
        if text is not None:
            return text.replace('\u00a0', ' ') 
        return ""
    
    @staticmethod
    def XLMtoDict(xml_file_path):
        # Read XML data from a file
        with open(xml_file_path, 'r') as file:
            xml_data = file.read()

        # Parse XML data
        root = ET.fromstring(xml_data)

        # Convert XML to a structured dictionary for JSON
        data = []
        for doc in root.findall('doc'):
            doc_data = {
                'id': None,
                'provided_text': None,
                'translated_text': None, 
                'enriched_text': None,
            }
            combined_text = []
            for field in doc.findall('field'):
                field_name = field.attrib['name']
                field_value = field.text
                if field_name == "europeana_id":
                    doc_data['id'] = field_value
                elif field_name in ["proxy_dc_title", "proxy_dc_creator", "proxy_dc_date"]:
                    if field_name == "proxy_dc_date":
                        name = "Date"
                    if field_name == "proxy_dc_title":
                        name = "Title"
                    if field_name == "proxy_dc_creator":
                        name = "Creator"
                    text = {str(name): str(field_value)}
                    # combined_text.append(Parser2.clean_text(text))
                    combined_text.append(text)
            # doc_data['text'] = " ".join(combined_text)
            doc_data['text'] = combined_text
            data.append(doc_data)

        return data
    
        # Function to extract and concatenate fields
    def extract_fields(doc):
        europeana_id = doc.find(".//field[@name='europeana_id']").text
        title = doc.find(".//provided_data/field[@name='dc_title']").text
        creator = doc.find(".//provided_data/field[@name='dc_creator']").text
        date = doc.find(".//provided_data/field[@name='dc_date']").text
        description = doc.find(".//provided_data/field[@name='dc_description']").text
        
        # Concatenate the fields into a single string
        id = f"ID: {europeana_id}"
        combined_fields = f"{title} by {creator}, dated {date}"
        return id, Parser2.clean_text(combined_fields)

    @staticmethod
    def XLMtoString(xml_file_path):
        # Read XML data from a file
        with open(xml_file_path, 'r') as file:
            xml_data = file.read()

        # Parse XML data
        root = ET.fromstring(xml_data)

       
        data = []

        # Extract data from each document
        documents = root.findall(".//doc")
        for doc in documents:
            doc_data = {
                'id': None,
                'text': None
            }
            id, combined_fields = Parser2.extract_fields(doc)
            # print(combined_fields)
            doc_data['id'] = id
            doc_data["text"] = combined_fields

            data.append(doc_data)

        return data
