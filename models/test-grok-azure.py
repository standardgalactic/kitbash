#!/usr/bin/python3

import os
import pathlib
from datetime import datetime
import logging
import sys
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

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
endpoint = os.environ.get("ENDPOINT")
api_key = os.environ.get("API_KEY")
model_name = os.environ.get("MODEL")

if not endpoint:
    raise ValueError("Environment variable ENDPOINT is not set.")
if not api_key:
    raise ValueError("Environment variable API_KEY is not set.")
if not model_name:
    raise ValueError("Environment variable MODEL is not set.")

# Initialize Azure client
client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(api_key)
)

# Define Documents folder and output file
documents_path = os.path.join(os.getcwd(), 'documents')
output_file = "responses.txt"

# Set up logging
logger = setup_logging(output_file)

def process_file(file_path):
    """Process a single text file and submit its content to the Azure AI Inference API."""
    logger.info(f"Processing file: {file_path}")
    
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read().strip()
        
        if not file_content:
            logger.warning(f"File {file_path} is empty, skipping.")
            return None
        
        # Construct messages with file content as context
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            UserMessage(content=f"Given the following context:\n{file_content}\n\nSummarize in detail and explain.")
        ]
        
        # Send API request
        response = client.complete(
            messages=messages,
            temperature=1.0,
            top_p=1.0,
            max_tokens=1000,
            model=model_name
        )
        
        # Validate response structure
        if not response.choices or not response.choices[0].message.content:
            raise ValueError("Unexpected response structure: Missing choices or content.")
        
        response_content = response.choices[0].message.content
        
        # Log summary to terminal and file
        summary = response_content[:100] + ("..." if len(response_content) > 100 else "")
        logger.info(f"Response summary for {file_path}: {summary}")
        
        # Write full response to output file
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(f"\n--- Response for {file_path} at {datetime.now().isoformat()} ---\n")
            f.write(response_content)
            f.write("\n\n")
        
        return response_content
    
    except HttpResponseError as http_err:
        logger.error(f"HTTP error for {file_path}: {http_err}")
        logger.error(f"Status code: {http_err.status_code}")
        logger.error(f"Response content: {http_err.response.text if http_err.response else '<no response>'}")
        return None
    
    except ValueError as val_err:
        logger.error(f"Response error for {file_path}: {val_err}")
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
