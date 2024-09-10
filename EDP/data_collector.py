import pandas as pd
import os
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed,ProcessPoolExecutor
from urllib.parse import quote_plus
from rdflib.namespace import RDF, DC, Namespace
import xml.etree.ElementTree as ET
from lxml import etree
import zipfile
import ftplib
import io
import csv
import field_extractor3 as fe
import os
import random
import lxml.etree as ET
import csv


# Constants
UNZIP_DIR = "selected_data"
FTP_HOST = "download.europeana.eu"
FTP_PATH = "dataset/XML/"
OUTPUT_DIR = "collected_data"
OUTPUT_DIR2 = "testing2"
CSV_PATH = '/home/sbasir/Thesis/Thesis/EDP/sample_data/datasets.csv'
TRANSLATIONS_DIR = '/home/sbasir/Thesis/Thesis/EDP/sample_data/translations/'


def read_csv_data(csv_path):
    with open('/home/sbasir/Thesis/Thesis/EDP/sample_data/datasets.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)

        limit = 300000

        # Extract 'ids' and 'lang' and save them in a dictionary, but only for rows where 'ndocs' is less than limit
        data_dict = {row['ids'] + '.zip': (row['lang'], row['ndocs']) for row in reader} #if int(row['ndocs']) < limit}

        csvfile.seek(0)  # Rewind the CSV file
        next(reader)  # Skip the header
        data_dict_alt = {row['ids'] + '.zip': (row['lang'], row['ndocs']) for row in reader if int(row['ndocs']) > limit}

        csvfile.seek(0)  # Rewind the CSV file
        next(reader)  # Skip the header

        # Extract only 'ids' in a separate list, but only for rows where 'ndocs' is less than limit
        data_ids = [row['ids'] + '.zip' for row in reader] #if int(row['ndocs']) < limit]

        csvfile.seek(0)  # Rewind the CSV file
        next(reader)  # Skip the header

        data_ids_alt = [row['ids'] + '.zip' for row in reader if int(row['ndocs']) > limit]

        return data_dict, data_ids

def get_translated_ids(data_dict):
    translated_ids = set()
    for filename, (lang, _) in data_dict.items():
        if lang != 'en':
            csv_path = os.path.join(TRANSLATIONS_DIR, filename.replace('.zip', '.csv'))
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                translated_ids.update(df['item_id'].values)
    return translated_ids

def download_file(ftp_host, ftp_path, filename):
    zip_data = io.BytesIO()
    with ftplib.FTP(ftp_host) as ftp:
        ftp.login()
        ftp.cwd(ftp_path)
        ftp.retrbinary(f'RETR {filename}', zip_data.write)
    zip_data.seek(0)
    return zip_data

def unzip_file(zip_data):
    extracted_files = []
    with zipfile.ZipFile(zip_data, 'r') as zip_ref:
        for file_info in zip_ref.infolist():
            file_name = file_info.filename  # Get the name of the file
            with zip_ref.open(file_info) as file:
                file_content = file.read()  # Read the file content
                extracted_files.append((file_name, file_content))  # Append a tuple of file name and content
    return extracted_files


def keep_random_10_percent(files):
    num_files_to_keep = max(1, int(len(files) * 0.10))
    print(f"keep {num_files_to_keep} documents from {len(files)}")
    return random.sample(files, num_files_to_keep)

def process_sample(args):
    sample, filename, i, translated_ids = args
    parsed = fe.parse_file(sample, translated_ids, filename)
    if parsed:
        # print("a")
        output_directory = f'{OUTPUT_DIR2}/{filename.replace(".zip", "")}'
        os.makedirs(output_directory, exist_ok=True)
        fe.write_data(parsed, output_directory, i+1)
    return i

def download_parsed_data(filename):
    print(f"Starting download and processing for {filename}...")
    try:
        lang, _ = data_dict.get(filename, ("", ""))
        zip_data = download_file(FTP_HOST, FTP_PATH, filename)
        extracted_files = unzip_file(zip_data)
        print(f"initial length for {filename}: {len(extracted_files)}")

        del zip_data
        
        print("a")
        if lang == 'en':
            print("b1")
            samples = keep_random_10_percent(extracted_files)
        else:
            print("b2")
            samples = [content for name, content in extracted_files 
               if name.split('/')[-1].replace('.xml', '') in translated_ids]

        print("c")
        total_samples = len(samples)
        print(f"final length for {filename}: {total_samples}")

        # Sequential processing without threading and without saving results
        for i, sample in enumerate(tqdm(samples, total=total_samples, desc=f"Processing {filename}")):
            process_sample((sample, filename, i, translated_ids))

        # with ProcessPoolExecutor(max_workers=8) as executor:
        #     args_list = [(sample, filename, i, translated_ids) for i, sample in enumerate(samples)]
        #     results = list(tqdm(executor.map(process_sample, args_list), total=total_samples, desc=f"Processing {filename}"))

        del extracted_files

    except Exception as e:
        print(f"Error processing {filename}: {e}")

if __name__ == '__main__':
    data_dict, data_ids = read_csv_data(CSV_PATH)
    data_ids = data_ids[:10]
    # print(data_dict)
    translated_ids = get_translated_ids(data_dict)
    with ProcessPoolExecutor(max_workers=8) as executor:
        list(executor.map(download_parsed_data, data_ids))
    # download_parsed_data(data_ids)