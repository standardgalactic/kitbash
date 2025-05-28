#!/usr/bin/python3

import os
import requests

# Validate environment variables
github_token = os.environ.get("GITHUB_TOKEN")
if not github_token:
    raise ValueError("Environment variable GITHUB_TOKEN is not set.")

endpoint = "https://models.github.ai/inference"
model_name = "xai/grok-3-mini"

# Define the API request
headers = {
    "Authorization": f"Bearer {github_token}",
    "Content-Type": "application/json"
}

payload = {
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the purpose of a null-wavefront in Null Convention Logic?"}
    ],
    "temperature": 1.0,
    "top_p": 1.0,
    "max_tokens": 1000,
    "model": model_name
}

try:
    # Send POST request to the chat completions endpoint
    response = requests.post(
        f"{endpoint.rstrip('/')}/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )
    
    # Log response details for debugging
    print(f"Response status code: {response.status_code}")
    print(f"Response headers: {response.headers}")
    print(f"Response content: {response.content.decode('utf-8', errors='replace')}")

    # Check for successful response
    response.raise_for_status()
    
    # Parse the response
    response_data = response.json()
    
    # Validate response structure
    if not response_data.get("choices") or not response_data["choices"][0].get("message", {}).get("content"):
        raise ValueError("Unexpected response structure: Missing choices or content.")
    
    # Print the response content
    print(response_data["choices"][0]["message"]["content"])

except requests.exceptions.HTTPError as http_err:
    # Handle HTTP errors (e.g., 401 Unauthorized, 404 Not Found)
    content = response.content.decode('utf-8', errors='replace') if response.content else "<empty response>"
    print(f"HTTP error occurred: {http_err}")
    print(f"Status code: {response.status_code}")
    print(f"Response content: {content}")
    raise

except requests.exceptions.JSONDecodeError as json_err:
    # Handle JSON parsing errors
    content = response.content.decode('utf-8', errors='replace') if response.content else "<empty response>"
    print(f"JSON decode error: {json_err}")
    print(f"Status code: {response.status_code}")
    print(f"Response content: {content}")
    raise

except requests.exceptions.RequestException as req_err:
    # Handle network or request errors
    print(f"Request error occurred: {req_err}")
    raise

except ValueError as val_err:
    # Handle response validation errors
    print(f"Response error: {val_err}")
    raise

except Exception as e:
    # Catch any other unexpected errors
    print(f"Unexpected error: {str(e)}")
    raise
