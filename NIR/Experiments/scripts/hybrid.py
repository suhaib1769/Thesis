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
from pymilvus import connections

import os
import gzip
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import tqdm 
import sys


# connections.connect("default", host="localhost", port="19530")

# if connections.has_connection("default"):
#     print("Successfully connected to Milvus")
# else:
#     print("Failed to connect to Milvus")

# # Define the data schema for the new Collection
# fields = [
#     # Use provided id as primary key
#     FieldSchema(name="pk", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
#     # Store the original text
#     FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
#     # Store dense vectors
#     FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=1024),  # Ensure the dimension matches your embeddings
#     # Store sparse vectors
#     FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),  
# ]

# schema = CollectionSchema(fields,  enable_dynamic_field=False)
# col_name = 'hybrid_experiment'
# col = Collection(col_name, schema, consistency_level="Strong")

# sparse_index = {"index_type": "SPARSE_INVERTED_INDEX", "metric_type": "IP"}
# col.create_index("sparse_vector", sparse_index)
# dense_index = {"index_type": "FLAT", "metric_type": "IP"}
# col.create_index("dense_vector", dense_index)
# col.load()

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
    try:
        data = merge_text_fields(batch_data)
        only_text = [x['text'] for x in data]

        # ef = BGEM3EmbeddingFunction(use_fp16=True, device='cuda')
        # ef2 = BGEM3EmbeddingFunction(use_fp16=False, device='cpu', return_sparse=True, return_dense=True, return_colbert_vecs=False)
        ef3 = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)

          # Generate embeddings using BGEM3 model
        embeddings = ef3.encode(only_text, return_sparse=True, return_dense=True, return_colbert_vecs=False)
        # Debug prints to verify the dimensions
        print(f"Number of texts: {len(only_text)}")
        print(f"Dense embeddings shape: {len(embeddings['dense_vecs'])}")
        print(f"Sparse embeddings shape: {len(embeddings['lexical_weights'])}")

        # Prepare data for insertion
        entities = [
            [item['id'] for item in data],  # IDs
            only_text,  # Texts
            embeddings["dense_vecs"],  # Dense vectors
            embeddings["lexical_weights"]  # Sparse vectors
        ]

        return entities

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


# Function to load data from a compressed JSON file
def load_compressed_json(file_path):
    """Function to load data from a compressed JSON file."""
    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
        return json.load(f)

# Function to load data in 64MB batches for Milvus indexing
def load_data_in_batches_for_indexing(parsed_directory, max_batch_size_mb=64, max_workers=4):
    """Load data from compressed JSON files in batches for indexing into Milvus."""
    max_batch_size_bytes = max_batch_size_mb * 1024 * 1024  # Convert MB to bytes
    batch_data = []  # To store the current batch
    batch_size = 0  # To track the size of the current batch in bytes

    # Collect all the .json.gz file paths
    file_paths = []
    for root, dirs, files in os.walk(parsed_directory):
        for file in files:
            if file.endswith('.json.gz'):
                file_path = os.path.join(root, file)
                file_paths.append(file_path)

    # Use ThreadPoolExecutor to load files in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(load_compressed_json, file_path): file_path for file_path in file_paths}

        for future in tqdm.tqdm(as_completed(future_to_file), total=len(future_to_file), desc="Loading and batching files"):
            file_path = future_to_file[future]
            try:
                data = future.result()  # Load the file's data
                data_size = sys.getsizeof(json.dumps(data))  # Get the size of this data in bytes

                # If the current batch size plus new data exceeds the limit, process the batch
                if (batch_size + data_size) > max_batch_size_bytes:
                    # Call your Milvus insertion function here
                    index_batch_into_milvus(batch_data)  # Replace this with your Milvus indexing function

                    # Reset the batch
                    batch_data = []
                    batch_size = 0

                # Add the data to the current batch
                batch_data.extend(data)  # Assuming data is a list of documents
                batch_size += data_size

            except Exception as e:
                print(f"Error loading file {file_path}: {e}")

    # Process any remaining data in the last batch
    if batch_data:
        index_batch_into_milvus(batch_data)  # Replace this with your Milvus indexing function

def index_batch_into_milvus(batch_data):
    print(f"Indexing batch with {len(batch_data)} documents into Milvus...")

    entities = hybrid_embeddings(batch_data)

    # Verify the lengths of each component to ensure they match
    print(f"Length of IDs: {len(entities[0])}")
    print(f"Length of texts: {len(entities[1])}")
    print(f"Shape of dense vectors: {len(entities[2])}")

    # col.insert(entities)
    # col.flush()

    print("Batch indexed successfully!")


    # run the function to load data in batches

load_data_in_batches_for_indexing('/home/sbasir/Thesis/Thesis/cp', max_batch_size_mb=64, max_workers=4)