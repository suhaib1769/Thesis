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
                'provided_data': "",
                'enriched_data': "",
                'translated_data': ""
            }

            # Extracting the document ID
            doc_id_field = doc.find(".//field[@name='europeana_id']")
            if doc_id_field is not None:
                doc_data['id'] = Parser2.clean_text(doc_id_field.text)

            # Extracting provided data fields
            provided_data = []
            provided_section = doc.find('provided_data')
            if provided_section is not None:
                for field in provided_section.findall('field'):
                    field_name = field.attrib['name']
                    field_value = Parser2.clean_text(field.text)
                    if field_value and field_value.lower() != 'none ':
                        provided_data.append(f"{field_name}: {field_value}")
                doc_data['provided_data'] = " ".join(provided_data)

            # Extracting enriched data fields
            enriched_data = []
            enriched_section = doc.find('enriched_data')
            if enriched_section is not None:
                for field in enriched_section.findall('field'):
                    field_name = field.attrib['name']
                    field_value = Parser2.clean_text(field.text)
                    if field_value and field_value.lower() != 'none ':
                        enriched_data.append(f"{field_name}: {field_value}")
                doc_data['enriched_data'] = " ".join(enriched_data)

            # Extracting translated data fields
            translated_data = []
            translated_section = doc.find('translated_data')
            if translated_section is not None:
                for field in translated_section.findall('field'):
                    field_name = field.attrib['name']
                    field_value = Parser2.clean_text(field.text)
                    if field_value and field_value.lower() != 'none ':
                        translated_data.append(f"{field_name}: {field_value}")
                doc_data['translated_data'] = " ".join(translated_data)

            data.append(doc_data)

        return data