import os
import gzip
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import tqdm
import sys

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
    """Dummy function to simulate Milvus indexing. Replace with actual Milvus logic."""
    print(f"Indexing batch with {len(batch_data)} documents into Milvus...")
    # Insert your Milvus batch indexing logic here

