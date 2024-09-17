import os
import json
import gzip
from concurrent.futures import ProcessPoolExecutor, as_completed
import tqdm
import re
from xml.sax.saxutils import unescape
import tqdm

# Function to clean and escape text, but avoid escaping XML tags like <value>
def clean_text(text):
    if text:
        text = text.strip()
        # Unescape any previously escaped entities to handle values correctly
        return unescape(text)
    return ""

# Function to extract fields using regular expressions and format as required
def extract_fields(xml_content, with_enriched=True, with_translated=True):
    doc_data = {
        'id': None,
        'text': "",
        'provided_data_text': "",
        'enriched_data_text': "",
        'translated_data_text': "",
    }

    # Regex patterns to extract fields
    patterns = {
        'id': re.compile(r'<field name="europeana_id">(.*?)</field>'),
        'timestamp_update': re.compile(r'<field name="timestamp_update">(.*?)</field>'),
        'type': re.compile(r'<field name="edm:type">(.*?)</field>'),
        'content_tier': re.compile(r'<field name="content_tier">(.*?)</field>'),
        'metadata_tier': re.compile(r'<field name="metadata_tier">(.*?)</field>')
    }

    # Collecting all the main fields into the 'text' key
    field_text_list = []
    for key, pattern in patterns.items():
        match = pattern.search(xml_content)
        if match:
            field_value = clean_text(match.group(1))
            if key != 'id':
                field_text_list.append(f"{key} is {field_value}")
            # Add the ID separately, but not other fields (they'll be in 'text')
            if key == 'id':
                doc_data['id'] = field_value

    
    doc_data['text'] = " | ".join(field_text_list)

    # Processing provided_data fields
    provided_data_content = extract_data_section(xml_content, 'provided_data')
    if provided_data_content:
        doc_data['provided_data'] = " | ".join([f"{k} is {v}" for item in provided_data_content for k, v in item.items()])

    # Processing enriched_data fields
    if with_enriched:
        enriched_data_content = extract_data_section(xml_content, 'enriched_data')
        if enriched_data_content:
            doc_data['enriched_data'] = " | ".join([f"{k} is {v}" for item in enriched_data_content for k, v in item.items()])

    # Processing translated_data fields
    if with_translated:
        translated_data_content = extract_data_section(xml_content, 'translated_data')
        if translated_data_content:
            doc_data['translated_data'] = " | ".join([f"{k} is {v}" for item in translated_data_content for k, v in item.items()])

    return doc_data

# Function to extract a data section
def extract_data_section(xml_content, section_name):
    data_list = []
    section_pattern = re.compile(f'<{section_name}>(.*?)</{section_name}>', re.DOTALL)
    section_match = section_pattern.search(xml_content)
    if section_match:
        section_content = section_match.group(1)
        field_pattern = re.compile(r'<field name="(.*?)">(.*?)</field>', re.DOTALL)
        for field_match in field_pattern.findall(section_content):
            value_pattern = re.compile(r'<value.*?>(.*?)</value>', re.DOTALL)
            values = value_pattern.findall(field_match[1])
            field_data = {field_match[0]: " | ".join([clean_text(v) for v in values])}
            data_list.append(field_data)
    return data_list

# Function to process XML file
def XMLtoDictNoParse(xml_file_path, with_enriched=True, with_translated=True):
    try:
        with open(xml_file_path, 'r', encoding='utf-8') as file:
            xml_content = file.read()
        doc_data = extract_fields(xml_content, with_enriched, with_translated)
        return doc_data
    except Exception as e:
        print(f"Error processing file {xml_file_path}: {e}")
        return None

# Function to save data to compressed JSON
def save_to_compressed_json(data, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)  # Ensure directory exists
    with gzip.open(output_file, 'wt', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

# Process a directory of XML files with concurrent.futures, including subdirectories
def process_xml_directory_no_parse(directory_path, output_directory, with_enriched=True, with_translated=True):
    print("Starting processing...")
    try:
        # Walk through the directory and subdirectories to get all XML files
        for root, dirs, files in os.walk(directory_path):
            for sub_dir in dirs:
                sub_dir_path = os.path.join(root, sub_dir)
                output_sub_dir_path = sub_dir_path.replace(directory_path, output_directory)
                
                # Get all XML files in the subdirectory
                file_list = []
                for root_sub, dirs_sub, files_sub in os.walk(sub_dir_path):
                    for file in files_sub:
                        if file.endswith('.xml'):
                            file_path = os.path.join(root_sub, file)
                            file_list.append(file_path)
                
                # Skip empty directories
                if not file_list:
                    continue

                print(f"Processing subdirectory: {sub_dir_path}")
                
                results = []  # List to store the results for this subdirectory
                
                # Use ProcessPoolExecutor for multiprocessing
                with ProcessPoolExecutor() as executor:
                    future_to_file = {executor.submit(XMLtoDictNoParse, file, with_enriched, with_translated): file for file in file_list}
                    
                    # As the futures complete, gather the results
                    for future in tqdm.tqdm(as_completed(future_to_file), total=len(future_to_file), desc=f"Processing {sub_dir}"):
                        file = future_to_file[future]
                        try:
                            data = future.result()
                            if data:
                                results.append(data)
                        except Exception as e:
                            print(f"Error processing file {file}: {e}")

                # Save the results to a compressed JSON file for the subdirectory
                output_file_path = os.path.join(output_sub_dir_path, f"{sub_dir}.json.gz")
                save_to_compressed_json(results, output_file_path)
                print(f"Saved compressed JSON for {sub_dir} to {output_file_path}")

    except Exception as e:
        print(f"Error processing directory {directory_path}: {e}")


# Usage example
xml_directory_path = '/home/sbasir/Thesis/Thesis/collected3'
output_directory_path = '/home/sbasir/Thesis/Thesis/collected3_parsed2'
process_xml_directory_no_parse(xml_directory_path, output_directory_path)
print("done with everything - happy indexing :)")