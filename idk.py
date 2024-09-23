import os
import shutil
from tqdm import tqdm

def split_data(source_dir, output_dir):
    # Get all files in the source directory and its subdirectories
    all_files = []
    for root, _, files in os.walk(source_dir):
        for file in files:
            all_files.append(os.path.join(root, file))
    
    # Sort files to ensure consistent ordering
    all_files.sort()
    
    # Calculate split points
    total_files = len(all_files)
    split_25 = int(total_files * 0.25)
    split_50 = int(total_files * 0.50)
    split_75 = int(total_files * 0.75)
    
    # Create output directories
    os.makedirs(os.path.join(output_dir, "25_percent"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "50_percent"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "75_percent"), exist_ok=True)
    
    # Copy files to respective directories with progress bar
    with tqdm(total=total_files, desc="Copying files") as pbar:
        for i, file in enumerate(all_files):
            rel_path = os.path.relpath(file, source_dir)
            if i < split_75:
                dest = os.path.join(output_dir, "75_percent", rel_path)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(file, dest)
                pbar.update(1)
            
            if i < split_50:
                dest = os.path.join(output_dir, "50_percent", rel_path)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(file, dest)
            
            if i < split_25:
                dest = os.path.join(output_dir, "25_percent", rel_path)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(file, dest)

if __name__ == "__main__":
    source_directory = "/home/sbasir/Thesis/Thesis/collected3"
    output_directory = "/home/sbasir/Thesis/Thesis/collected3_split"
    split_data(source_directory, output_directory)