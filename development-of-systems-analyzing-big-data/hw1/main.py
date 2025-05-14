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

# Constants
DATA_DIR = './datasets'

def create_directories(dataset_id):
    """Create necessary directories for the dataset"""
    dataset_dir = os.path.join(DATA_DIR, dataset_id)
    raw_dir = os.path.join(dataset_dir, 'raw')
    processed_dir = os.path.join(dataset_dir, 'processed')
    
    for directory in [DATA_DIR, dataset_dir, raw_dir, processed_dir]:
        os.makedirs(directory, exist_ok=True)
    
    return dataset_dir, raw_dir, processed_dir

def download_dataset(dataset_id, raw_dir):
    """Download dataset from GEO"""
    # Create the base URL for the dataset
    dataset_page_url = f'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={dataset_id}'
    
    # Fetch the dataset page
    response = requests.get(dataset_page_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch dataset page: {response.status_code}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the download link for RAW.tar
    download_link = None
    for link in soup.find_all('a', href=True):
        if f'{dataset_id}_RAW.tar' in link.text:
            download_link = link['href']
            if not download_link.startswith('http'):
                download_link = 'https://www.ncbi.nlm.nih.gov' + download_link
            break
    
    if not download_link:
        # Use the provided link as fallback
        download_link = f'https://www.ncbi.nlm.nih.gov/geo/download/?acc={dataset_id}&format=file'
    
    # Download the file
    tar_path = os.path.join(raw_dir, f'{dataset_id}_RAW.tar')
    print(f"Downloading {download_link} to {tar_path}")
    
    # Using requests
    response = requests.get(download_link, stream=True)
    with open(tar_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"Download completed: {tar_path}")
    return tar_path

def extract_tar(tar_path, raw_dir):
    """Extract the tar archive and return a list of extracted files"""
    print(f"Extracting {tar_path}")
    with tarfile.open(tar_path) as tar:
        tar.extractall(path=raw_dir)
    
    # Get the list of extracted files (excluding directories)
    files = [f for f in os.listdir(raw_dir) if os.path.isfile(os.path.join(raw_dir, f)) and f != os.path.basename(tar_path)]
    print(f"Extracted {len(files)} files: {', '.join(files)}")
    return files

def process_gz_file(gz_file, raw_dir, processed_dir):
    """Process a gzipped file, extract tables and save as TSV"""
    gz_path = os.path.join(raw_dir, gz_file)
    file_name = os.path.splitext(gz_file)[0]
    file_dir = os.path.join(processed_dir, file_name)
    os.makedirs(file_dir, exist_ok=True)
    
    # Extract the gzipped file
    txt_path = os.path.join(file_dir, f"{file_name}.txt")
    with gzip.open(gz_path, 'rb') as f_in:
        with open(txt_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    # Process the tables in the text file
    dfs = {}
    with open(txt_path) as f:
        write_key = None
        fio = io.StringIO()
        for l in f.readlines():
            if l.startswith('['):
                if write_key:
                    fio.seek(0)
                    header = None if write_key == 'Heading' else 'infer'
                    dfs[write_key] = pd.read_csv(fio, sep='\t', header=header)
                fio = io.StringIO()
                write_key = l.strip('[]\n')
                continue
            if write_key:
                fio.write(l)
        fio.seek(0)
        if write_key:
            dfs[write_key] = pd.read_csv(fio, sep='\t')
    
    # Save each table as a separate TSV file
    for table_name, df in dfs.items():
        table_file = os.path.join(file_dir, f"{table_name}.tsv")
        df.to_csv(table_file, sep='\t', index=False)
        print(f"Saved table {table_name} to {table_file}")
        
        # Create reduced version of the Probes table
        if table_name == 'Probes':
            columns_to_remove = ['Definition', 'Ontology_Component', 'Ontology_Process', 
                                'Ontology_Function', 'Synonyms', 'Obsolete_Probe_Id', 
                                'Probe_Sequence']
            reduced_df = df.drop(columns=[col for col in columns_to_remove if col in df.columns])
            reduced_file = os.path.join(file_dir, f"{table_name}_reduced.tsv")
            reduced_df.to_csv(reduced_file, sep='\t', index=False)
            print(f"Saved reduced {table_name} table to {reduced_file}")
    
    # Remove the original text file if all tables were successfully saved
    if len(dfs) > 0:
        os.remove(txt_path)
        print(f"Removed original text file: {txt_path}")
    
    return dfs.keys()

def main(dataset_id):
    """Main function to orchestrate the pipeline"""
    # Step 1: Create directories
    dataset_dir, raw_dir, processed_dir = create_directories(dataset_id)
    
    # Step 2: Download the dataset
    tar_path = download_dataset(dataset_id, raw_dir)
    
    # Step 3: Extract the tar archive
    extracted_files = extract_tar(tar_path, raw_dir)
    
    # Step 4: Process each gzipped file
    for gz_file in extracted_files:
        if gz_file.endswith('.gz'):
            table_names = process_gz_file(gz_file, raw_dir, processed_dir)
            print(f"Processed {gz_file}, found tables: {', '.join(table_names)}")
    
    print(f"Processing completed for dataset {dataset_id}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        dataset_id = sys.argv[1]
    else:
        dataset_id = 'GSE68849'  # Default dataset ID
    
    main(dataset_id)
