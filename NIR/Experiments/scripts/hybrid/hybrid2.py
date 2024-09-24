import random
import string
import numpy as np
from milvus import default_server
from pymilvus import (
    utility,
    FieldSchema, CollectionSchema, DataType,
    Collection, AnnSearchRequest, RRFRanker, connections,
)
from pymilvus.model.hybrid import BGEM3EmbeddingFunction
from FlagEmbedding import BGEM3FlagModel
import torch
from pymilvus import connections
from pymilvus import connections, list_collections, drop_collection
import os
import gzip
import json
import time
import tqdm
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


connections.connect("default", host="localhost", port="19530")

if connections.has_connection("default"):
    print("Successfully connected to Milvus")
else:
    print("Failed to connect to Milvus")


# Connect to Milvus server
connections.connect(alias="default", host="localhost", port="19530")

# List all collections in Milvus
collections = list_collections()
print(f"Collections in Milvus: {collections}")

# Define the data schema for the new Collection
fields = [
    # Use provided id as primary key
    FieldSchema(name="pk", dtype=DataType.VARCHAR, is_primary=True, max_length=1000),
    # Store the original text
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    # Store dense vectors
    FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
    # Store sparse vectors
    FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),  
]

schema = CollectionSchema(fields,  enable_dynamic_field=False)
col_name = 'hybrid_experiment_test2'
col = Collection(col_name, schema, consistency_level="Strong")


sparse_index = {"index_type": "SPARSE_INVERTED_INDEX", "metric_type": "IP"}
col.create_index("sparse_vector", sparse_index)
dense_index = {"index_type": "FLAT", "metric_type": "IP"}
col.create_index("dense_vector", dense_index)
col.load()

ef = BGEM3EmbeddingFunction(use_fp16=True, device='cuda')


def merge_text_fields(data):
    for item in data:
        # Merge the fields into 'text', separating them by " | "
        merged_text = " | ".join(filter(None, [item.get('text', ''), 
                                            item.get('provided_data', ''), 
                                            item.get('enriched_data', ''), 
                                            item.get('translated_data', '')]))
        
        # Assign the merged text back to the 'text' field
        item['text'] = merged_text
        
        # Remove the individual fields as they're now part of 'text'
        item.pop('provided_data', None)
        item.pop('enriched_data', None)
        item.pop('translated_data', None)
    
    return data

def hybrid_embeddings(batch_data):
    data = merge_text_fields(batch_data)
    only_text = [x['text'] for x in data]

    # Generate embeddings using BGEM3 model
    embeddings = ef.encode(only_text)
    
    # make sure all dense vectors are float32
    embeddings["dense"] = np.array(embeddings["dense"], dtype=np.float32)

    # Prepare data for insertion
    entities = [
        [item['id'] for item in data],  # IDs
        only_text,  # Texts
        embeddings["dense"],  # Dense vectors
        embeddings["sparse"]  # Sparse vectors
    ]

    del embeddings
    # torch.cuda.empty_cache()

    return entities

docs_len_vals = [128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1000000]

# Function to load data from a compressed JSON file
def load_compressed_json(file_path):
    """Function to load data from a compressed JSON file."""
    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
        return json.load(f)

def load_data_in_batches_for_indexing(uncompressed_data, batch_size=100):
    """Index pre-loaded (uncompressed) data in batches for Milvus."""
    batch_data = []  # To store the current batch
    start_time = time.time()  # Record the start time
    total_docs_indexed = 0  # Track the total number of documents indexed

    checkpoint_times = {}  # Dictionary to save checkpoint times
    timestamp_file = f'timestamps_uncompressed.txt'

    # Loop over uncompressed data to process in batches
    for doc in tqdm.tqdm(uncompressed_data, desc="Batching and Indexing Data"):
        batch_data.append(doc)

        # Process in exact batches of 'batch_size' documents
        if len(batch_data) >= batch_size:
            # print(f"Processing batch with {batch_size} documents...")
            index_batch_into_milvus(batch_data[:batch_size])  # Process exactly 'batch_size' documents

            # Remove the processed documents from the batch
            del batch_data[:batch_size]

            # Update the total number of documents indexed
            total_docs_indexed += batch_size

            # Check if the total indexed documents exceed the next threshold in docs_len_vals
            while docs_len_vals and total_docs_indexed >= docs_len_vals[0]:
                checkpoint_times[docs_len_vals[0]] = time.time() - start_time
                print(f"Reached {docs_len_vals[0]} documents in {checkpoint_times[docs_len_vals[0]]:.2f} seconds.")
                docs_len_vals.pop(0)

                with open(timestamp_file, 'w') as f:
                    json.dump(checkpoint_times, f)
                print(f"Checkpoint times saved to '{timestamp_file}'.")

    # Process any remaining documents
    if batch_data:
        # print(f"Processing final batch with {len(batch_data)} documents...")
        index_batch_into_milvus(batch_data)

    # Save the final checkpoint times to a file
    with open('checkpoint_times.json', 'w') as f:
        json.dump(checkpoint_times, f)
    # print("Checkpoint times saved to 'checkpoint_times.json'.")

def index_batch_into_milvus(batch_data):
    # print(f"Indexing batch with {len(batch_data)} documents into Milvus...")
    
    entities = hybrid_embeddings(batch_data)
    print(torch.cuda.memory_summary(device=None, abbreviated=False))
    col.insert(entities)
    col.flush()
    print(torch.cuda.memory_summary(device=None, abbreviated=False))

    del entities

def embed_and_index(parsed_directory, batch_size=100, max_workers=4):
    """Process one dataset at a time without loading all data at once."""
    # Collect all the .json.gz file paths
    file_paths = []
    for root, dirs, files in os.walk(parsed_directory):
        for file in files:
            if file.endswith('.json.gz'):
                file_path = os.path.join(root, file)
                file_paths.append(file_path)
    
    total_files = len(file_paths)
    print(f"Found {total_files} files to process.")

    # Loop over each compressed file, uncompress, and process it
    for file_path in tqdm.tqdm(file_paths, desc="Processing files"):
        try:
            print(file_path)
            uncompressed_data = load_compressed_json(file_path)
            
            load_data_in_batches_for_indexing(uncompressed_data, batch_size=batch_size)
            
            del uncompressed_data
            
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")

embed_and_index('/home/sbasir/Thesis/Thesis/cp2', batch_size=1, max_workers=1)
print(torch.cuda.memory_summary(device=None, abbreviated=False))