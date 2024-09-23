import os
import shutil
from tqdm import tqdm

def extract_last_25_percent(dir_75, dir_100, output_dir):
    # Create output directory
    output_subdir = "75_100_percentile"
    os.makedirs(os.path.join(output_dir, output_subdir), exist_ok=True)

    # Function to get all files in a directory
    def get_files(directory):
        file_list = []
        for root, _, files in os.walk(directory):
            for file in files:
                file_list.append(os.path.relpath(os.path.join(root, file), directory))
        return set(file_list)

    # Get files for 75% and 100% directories
    files_75 = get_files(dir_75)
    files_100 = get_files(dir_100)

    # Calculate the last 25%
    files_75_100 = files_100 - files_75

    # Copy files to the output directory with progress bar
    with tqdm(total=len(files_75_100), desc="Extracting second 25%") as pbar:
        for file in files_75_100:
            source = os.path.join(dir_100, file)
            dest = os.path.join(output_dir, output_subdir, file)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(source, dest)
            pbar.update(1)

    print(f"Extracted {len(files_75_100)} files to {os.path.join(output_dir, output_subdir)}")

if __name__ == "__main__":
    dir_75 = "/home/sbasir/Thesis/Thesis/collected3_split/25_percent"
    dir_100 = "/home/sbasir/Thesis/Thesis/collected3_split/50_percent"
    output_directory = "/home/sbasir/Thesis/Thesis/collected3_split/25_2_percent"
    extract_last_25_percent(dir_75, dir_100, output_directory)