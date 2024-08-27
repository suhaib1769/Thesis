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

# Define your API key
api_key = 'ntioungsta'

# Load dataset
df = pd.read_csv('/Users/suhaibbasir/Documents/CS/MSc/Thesis/Thesis/EDP/europeana_datasets - europeana_datasets.csv')
df.head()

# Get first dataset name
dataset_name = df.iloc[0][0]
print(dataset_name)

# Define the number of rows per request
rows = 100

# Initialize cursor for pagination
cursor = '*'

# Initialize list to store document IDs and documents
document_ids = []
documents = []

# Set a limit for the maximum number of requests
max_requests = 20  # Adjust based on how many documents you need
current_request = 0

# Function to get documents using cursor-based pagination
def get_documents(api_key, dataset_name, rows, cursor):
    search_url = f'https://api.europeana.eu/record/v2/search.json?wskey={api_key}&query=*&qf=edm_datasetName:"{dataset_name}"&rows={rows}&cursor={cursor}'
    response = requests.get(search_url)
    data = response.json()
    # Check if 'items' key is in the response
    if 'items' in data:
        document_ids = [item['id'] for item in data['items']]
    else:
        document_ids = []
    
    next_cursor = data.get('nextCursor', None)
    safe_next_cursor = quote_plus(next_cursor) if next_cursor else None
    # print(f'Next cursor: {next_cursor}')
    return document_ids, safe_next_cursor

# Function to fetch document by ID
def fetch_document(api_key, doc_id):
    record_url = f'https://api.europeana.eu/record/v2/{doc_id}.rdf?wskey={api_key}'
    response = requests.get(record_url)
    return response.text

# Loop to paginate through results
while cursor and current_request < max_requests:
    print(f'Request #{current_request + 1}')
    current_request += 1
    new_document_ids, cursor = get_documents(api_key, dataset_name, rows, cursor)
    
    document_ids.extend(new_document_ids)

    # Debug information
    print(f'Cursor: {cursor}')
    print(f'Number of documents retrieved in this request: {len(new_document_ids)}')
    print(f'Total documents retrieved so far: {len(document_ids)}')

    # Fetch each document by its ID using concurrent requests
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_doc = {executor.submit(fetch_document, api_key, doc_id): doc_id for doc_id in new_document_ids}
        for future in as_completed(future_to_doc):
            try:
                documents.append(future.result())
            except Exception as e:
                print(f"An error occurred: {e}")
    
    # To avoid hitting the API rate limit
    time.sleep(1)  # Adjust sleep time as needed

# Check the number of documents collected
print(f'Total documents collected: {len(documents)}')