#!/usr/bin/python3

import os
import requests
import pathlib
from datetime import datetime
import logging
import sys

# Configure logging to tee output to both terminal and file
def setup_logging(output_file):
    logger = logging.getLogger("NCLProcessor")
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(output_file, mode='a')
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)
    
    return logger

# Validate environment variables
github_token = os.environ.get("GITHUB_TOKEN")
if not github_token:
    raise ValueError("Environment variable GITHUB_TOKEN is not set.")

# Define endpoint and model
endpoint = "https://models.github.ai/inference/chat/completions"
model_name = "xai/grok-3-mini"

# Define Documents folder
documents_path = os.path.join(os.getcwd(), 'documents')
output_file = "responses.txt"

# Set up logging
logger = setup_logging(output_file)

# Define API headers
headers = {
    "Authorization": f"Bearer {github_token}",
    "Content-Type": "application/json",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

def process_file(file_path):
    """Process a single text file and submit its content to the API."""
    logger.info(f"Processing file: {file_path}")
    
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read().strip()
        
        if not file_content:
            logger.warning(f"File {file_path} is empty, skipping.")
            return None
        
        # Construct payload with file content as context
        payload = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Given the following context:\n{file_content}\n\nSummarize in detail and explain."}
            ],
            "temperature": 1.0,
            "top_p": 1.0,
            "max_tokens": 1000,
            "model": model_name
        }
        
        # Send API request
        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        # Parse response
        response_data = response.json()
        if not response_data.get("choices") or not response_data["choices"][0].get("message", {}).get("content"):
            raise ValueError("Unexpected response structure: Missing choices or content.")
        
        response_content = response_data["choices"][0]["message"]["content"]
        
        # Log summary to terminal and file
        summary = response_content[:100] + ("..." if len(response_content) > 100 else "")
        logger.info(f"Response summary for {file_path}: {summary}")
        
        # Write full response to output file
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(f"\n--- Response for {file_path} at {datetime.now().isoformat()} ---\n")
            f.write(response_content)
            f.write("\n\n")
        
        return response_content
    
    except requests.exceptions.HTTPError as http_err:
        content = response.content.decode('utf-8', errors='replace') if response.content else "<empty response>"
        logger.error(f"HTTP error for {file_path}: {http_err}")
        logger.error(f"Status code: {response.status_code}")
        logger.error(f"Response content: {content}")
        return None
    
    except requests.exceptions.JSONDecodeError as json_err:
        content = response.content.decode('utf-8', errors='replace') if response.content else "<empty response>"
        logger.error(f"JSON decode error for {file_path}: {json_err}")
        logger.error(f"Status code: {response.status_code}")
        logger.error(f"Response content: {content}")
        return None
    
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request error for {file_path}: {req_err}")
        return None
    
    except Exception as e:
        logger.error(f"Unexpected error for {file_path}: {str(e)}")
        return None

def main():
    """Find and process all .txt files in the Documents folder."""
    documents_dir = pathlib.Path(documents_path)
    if not documents_dir.exists():
        logger.error(f"Documents directory does not exist: {documents_dir}")
        return
    
    txt_files = list(documents_dir.glob("*.txt"))
    if not txt_files:
        logger.warning(f"No .txt files found in {documents_dir}")
        return
    
    logger.info(f"Found {len(txt_files)} .txt files in {documents_dir}")
    
    for file_path in txt_files:
        process_file(file_path)
    
    logger.info("Processing complete.")

if __name__ == "__main__":
    main()
