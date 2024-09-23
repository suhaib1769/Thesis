import numpy as np
from milvus import default_server
from pymilvus import (
    utility,
    FieldSchema, CollectionSchema, DataType,
    Collection, AnnSearchRequest, RRFRanker, connections,
)
from pymilvus.model.hybrid import BGEM3EmbeddingFunction
from sentence_transformers import SentenceTransformer
import pandas as pd
# Load model directly
from transformers import AutoTokenizer, AutoModelForMaskedLM
from pymilvus import connections, list_collections
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import gzip
import json
import time
import tqdm

connections.connect("default", host="localhost", port="19530")

if connections.has_connection("default"):
    print("Successfully connected to Milvus")
else:
    print("Failed to connect to Milvus")

# Define the data schema for the new Collection
fields = [
    # Use provided id as primary key
    FieldSchema(name="pk", dtype=DataType.VARCHAR, is_primary=True, max_length=1000),
    # Store the original text
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    # Store dense vectors
    FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=512),  # Ensure the dimension matches your embeddings
]

schema = CollectionSchema(fields,  enable_dynamic_field=False)
col_name = 'sbert_experiment'
col = Collection(col_name, schema, consistency_level="Strong")

dense_index = {"index_type": "FLAT", "metric_type": "IP"}
col.create_index("dense_vector", dense_index)
col.load()

model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased-v2', device='cuda')

def merge_and_chunk_text_fields(data, limit=128):
    chunked_data = []
    
    for item in data:
        # Merge the fields into 'text', separating them by " | "
        merged_text = " | ".join(filter(None, [item.get('text', ''), 
                                               item.get('provided_data', ''), 
                                               item.get('enriched_data', ''), 
                                               item.get('translated_data', '')]))
        
        # Apply the chunker function on the merged text
        chunks = chunker([merged_text], limit)
        
        # Append each chunk with an ID
        for i, chunk in enumerate(chunks):
            chunk_id = f'{item["id"]}_{i}'
            chunked_data.append({'id': chunk_id, 'text': chunk})
    
    return chunked_data


# Reusing your chunker function and adjusting it to take a limit as a parameter
def chunker(contexts: list, limit):
    chunks = []
    all_contexts = ' '.join(contexts).split('.')
    chunk = []
    for context in all_contexts:
        chunk.append(context)
        if len(chunk) >= 3 and len('.'.join(chunk)) > limit:
            # surpassed limit so add to chunks and reset
            chunks.append('.'.join(chunk).strip() + '.')
            # add some overlap between passages
            chunk = chunk[-2:]
    # if we finish and still have a chunk, add it
    if chunk:
        chunks.append('.'.join(chunk).strip() + '.')
    return chunks

def sbert_embeddings(batch_data):
    data = merge_and_chunk_text_fields(batch_data)
    # print(data[0])
    embeddings = model.encode([x['text'] for x in data])

    # Prepare data for insertion
    entities = [
        [item['id'] for item in data], #IDs
        [item['text'] for item in data], #Text
        embeddings #Embeddings
    ]

    del embeddings

    return entities

# Function to load data from a compressed JSON file
def load_compressed_json(file_path):
    """Function to load data from a compressed JSON file."""
    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
        return json.load(f)

# Function to load data in batches of 1000 documents for Milvus indexing
def load_data_in_batches_for_indexing(parsed_directory, batch_size=1000, max_workers=4):
    """Load data from compressed JSON files in batches for indexing into Milvus."""
    batch_data = []  # To store the current batch
    start_time = time.time()  # Record the start time

    # Collect all the .json.gz file paths
    file_paths = []
    for root, dirs, files in os.walk(parsed_directory):
        for file in files:
            if file.endswith('.json.gz'):
                file_path = os.path.join(root, file)
                file_paths.append(file_path)

    total_files = len(file_paths)
    checkpoint_times = {}  # Dictionary to save checkpoint times
    timestamp_file = f'timestamps_{parsed_directory.replace("/", "_")}.txt'

    # Use ThreadPoolExecutor to load files in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(load_compressed_json, file_path): file_path for file_path in file_paths}

        for idx, future in enumerate(tqdm.tqdm(as_completed(future_to_file), total=total_files, desc="Loading and batching files")):
            file_path = future_to_file[future]
            try:
                data = future.result()  # Load the file's data
                
                # Add the data to the current batch
                batch_data.extend(data)  # Assuming data is a list of documents

                # If the current batch exceeds the batch size, process it
                if len(batch_data) >= batch_size:
                    # Call your Milvus insertion function here
                    index_batch_into_milvus(batch_data[:batch_size])  # Process batch_size documents at a time

                    # Remove the processed documents from the batch
                    batch_data = batch_data[batch_size:]

                # Record the time at each 10% completion
                percentage_complete = ((idx + 1) / total_files) * 100
                print(f"percentage_complete: {percentage_complete}")
                if percentage_complete >= 10 and (int(percentage_complete) % 10 == 0):
                    elapsed_time = time.time() - start_time
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    log_entry = f"Indexed {int(percentage_complete)}% of documents in {elapsed_time:.2f} seconds at {timestamp}\n"
                    
                    # Append the log entry to the timestamp file
                    with open(timestamp_file, 'a') as f:
                        f.write(log_entry)
                    
                    print(log_entry.strip())

            except Exception as e:
                print(f"Error loading file {file_path}: {e}")

    # Process any remaining data in the last batch
    if batch_data:
        index_batch_into_milvus(batch_data)  # Replace this with your Milvus indexing function

def index_batch_into_milvus(batch_data):
    print(f"Indexing batch with {len(batch_data)} documents into Milvus...")

    entities = sbert_embeddings(batch_data)

    # Verify the lengths of each component to ensure they match
    print(f"Length of IDs: {len(entities[0])}")
    print(f"Length of texts: {len(entities[1])}")
    print(f"Shape of dense vectors: {len(entities[2])}")

    col.insert(entities)
    col.flush()

    del entities

    print("Batch indexed successfully.")

# run the function to load data in batches
directory = '/home/sbasir/Thesis/Thesis/collected3_parsed2_split_25_3'
load_data_in_batches_for_indexing(directory, max_workers=4)
print(f"done indexing sbert embeddings for {directory}")
