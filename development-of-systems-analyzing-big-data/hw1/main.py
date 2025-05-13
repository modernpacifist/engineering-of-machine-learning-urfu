#!/bin/env python3

import io
import pandas as pd
import os
import requests
import subprocess
from bs4 import BeautifulSoup
import re
import tarfile
import gzip
import shutil

DATASET_LINK = 'https://www.ncbi.nlm.nih.gov/geo/download/?acc=GSE68849&format=file'
DATA_DIR = './datasets'


def fetch_dataset(url=DATASET_LINK, save_path='./datasets/GSE68849_data.rar'):
    # Check if the file already exists
    if os.path.exists(save_path):
        print(f"Dataset already exists at {save_path}")
        return save_path
    
    # File doesn't exist, so download it
    print(f"Downloading dataset from {url}...")
    response = requests.get(url)
    
    # Check if the download was successful
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(response.content)
        print(f"Dataset downloaded and saved to {save_path}")
        return save_path
    else:
        raise Exception(f"Failed to download dataset: HTTP status code {response.status_code}")


def extract_tar_archive(tar_filepath, extract_dir=None):
    """
    Extract a TAR archive and return info about extracted files.
    
    Args:
        tar_filepath (str): Path to the TAR file
        extract_dir (str): Directory to extract files to. If None, uses parent directory of TAR file.
        
    Returns:
        list: List of dictionaries with info about extracted files
    """
    if extract_dir is None:
        extract_dir = os.path.dirname(tar_filepath)
    
    # Check if file exists and has content
    if not os.path.exists(tar_filepath):
        raise FileNotFoundError(f"TAR file not found at {tar_filepath}")
    
    file_size = os.path.getsize(tar_filepath)
    if file_size == 0:
        raise ValueError(f"TAR file is empty (0 bytes): {tar_filepath}")
    
    print(f"Attempting to extract TAR file: {tar_filepath} (Size: {file_size} bytes)")
    
    # Get base name without extension for creating subdirectory
    base_name = os.path.basename(tar_filepath).split('.')[0]
    extraction_root = os.path.join(extract_dir, f"{base_name}_extracted")
    
    # Check if extraction directory already exists and has content
    if os.path.exists(extraction_root) and os.listdir(extraction_root):
        print(f"Extraction directory {extraction_root} already exists with content. Skipping extraction.")
        # Gather information about existing files
        extracted_files = []
        for root, dirs, files in os.walk(extraction_root):
            for file in files:
                file_path = os.path.join(root, file)
                file_info = {
                    'name': file,
                    'size': os.path.getsize(file_path),
                    'extraction_dir': root,
                    'extracted_path': file_path
                }
                extracted_files.append(file_info)
        return extracted_files
    
    # Create extraction directory if it doesn't exist
    os.makedirs(extraction_root, exist_ok=True)
    
    extracted_files = []
    
    with tarfile.open(tar_filepath, 'r') as tar:
        members = tar.getmembers()
        print(f"Found {len(members)} files in the archive")
        
        for member in members:
            if member.isfile():  # Skip directories
                # Create individual directory for each file
                file_name = os.path.basename(member.name)
                file_dir = os.path.join(extraction_root, os.path.splitext(file_name)[0])
                os.makedirs(file_dir, exist_ok=True)
                
                # Extract file to its directory
                file_info = {
                    'name': file_name,
                    'size': member.size,
                    'extraction_dir': file_dir,
                    'extracted_path': os.path.join(file_dir, file_name)
                }
                
                # Extract the file
                tar.extract(member, path=file_dir)
                extracted_files.append(file_info)
                print(f"Extracted {file_name} to {file_dir}")
    
    return extracted_files

def extract_gzip_files(files_info):
    """
    Process gzipped files from a list of file information dictionaries.
    
    Args:
        files_info (list): List of dictionaries with file information
        
    Returns:
        list: Updated file information with extracted content paths
    """
    for file_info in files_info:
        file_path = file_info['extracted_path']
        
        if file_path.endswith('.gz'):
            output_path = file_path[:-3]  # Remove the .gz extension
            
            # Extract the gzipped file
            with gzip.open(file_path, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            print(f"Extracted gzipped file: {output_path}")
            file_info['uncompressed_path'] = output_path
            
            # If it's a text file, check for multiple TSV tables
            if output_path.endswith('.txt'):
                split_tsv_tables(output_path, file_info['extraction_dir'])
    
    return files_info

def split_tsv_tables(text_file_path, output_dir):
    """
    Split a text file containing multiple TSV tables into separate files.
    Tables are identified by headers starting with '['.
    
    Args:
        text_file_path (str): Path to the text file
        output_dir (str): Directory to save the split tables
        
    Returns:
        list: Paths to the created TSV files
    """
    with open(text_file_path, 'r') as file:
        content = file.read()
    
    # Find table headers starting with '['
    table_pattern = r'(\[\S+.*?)(?=\[\S+|\Z)'
    tables = re.findall(table_pattern, content, re.DOTALL)
    
    output_files = []
    
    if tables:
        print(f"Found {len(tables)} TSV tables in {text_file_path}")
        
        for i, table_content in enumerate(tables):
            # Extract the header title from the first line
            header_match = re.match(r'\[(\S+)[^\n]*', table_content)
            if header_match:
                table_name = header_match.group(1)
            else:
                table_name = f"table_{i+1}"
            
            # Create a clean filename
            file_name = f"{table_name}.tsv"
            output_path = os.path.join(output_dir, file_name)
            
            # Write the table to a separate file
            with open(output_path, 'w') as out_file:
                out_file.write(table_content.strip())
            
            print(f"Saved table to {output_path}")
            output_files.append(output_path)
    else:
        print(f"No TSV tables with '[' headers found in {text_file_path}")
    
    return output_files

def process_dataset(dataset_file):
    """
    Process the downloaded dataset file.
    
    Args:
        dataset_file (str): Path to the dataset file
        
    Returns:
        list: List of extracted TSV files
    """
    # Extract the archive
    extracted_files_info = extract_tar_archive(dataset_file)
    
    # Process any gzipped files
    processed_files = extract_gzip_files(extracted_files_info)
    
    # Collect all TSV files
    all_tsv_files = []
    for file_info in processed_files:
        if 'uncompressed_path' in file_info and file_info['uncompressed_path'].endswith('.tsv'):
            all_tsv_files.append(file_info['uncompressed_path'])
        elif file_info['extracted_path'].endswith('.tsv'):
            all_tsv_files.append(file_info['extracted_path'])
    
    print(f"Total TSV tables extracted: {len(all_tsv_files)}")
    return all_tsv_files


def pipeline_run(dataset_id="GSE68849"):
    """
    Complete pipeline for downloading and processing a GEO dataset.
    
    Args:
        dataset_id (str): GEO dataset ID
        
    Returns:
        dict: Information about the processed dataset
    """
    # Create datasets directory
    datasets_dir = DATA_DIR
    os.makedirs(datasets_dir, exist_ok=True)
    
    # Download the dataset
    dataset_file = fetch_dataset()
    
    # Extract and process files from the archive
    if dataset_file and os.path.exists(dataset_file):
        # Extract the archive
        extracted_files_info = extract_tar_archive(dataset_file)
        
        # Process the extracted files
        processed_files = extract_gzip_files(extracted_files_info)
        
        # Get the extraction root directory
        if processed_files:
            extraction_root = os.path.dirname(processed_files[0]['extracted_path'])
            tsv_files = process_dataset(dataset_file)
        else:
            print(f"Warning: No files were extracted")
            tsv_files = []
            
        return {
            'dataset_id': dataset_id,
            'dataset_file': dataset_file,
            'extracted_files': processed_files,
            'tsv_files': tsv_files
        }
    else:
        raise Exception("Failed to process dataset: Dataset file not found")


if __name__ == "__main__":
    # Run the full pipeline
    process_result = pipeline_run("GSE68849")
    print(f"Processed {len(process_result['extracted_files'])} files from dataset GSE68849")
