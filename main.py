import json
import os
from pathlib import Path

import requests
from tqdm import tqdm


def asking_ai(content):
    # Set up the base URL for the local Ollama API
    url = "http://localhost:11434/api/chat"

    prompt = """You are an AI assistant specialized in analyzing code files. Your task is to read the provided code file and generate a clear, concise explanation of its purpose and functionality. This explanation is intended to help current and future developers understand the file's role within the web application.

Instructions:

File Overview: Begin with a brief summary of the file's primary purpose.

Functionality Breakdown: Describe the main components, functions, classes, or logic structures present in the code. Explain how they contribute to the file's overall purpose.

Integration Context: Explain how this file interacts with other parts of the application, such as dependencies, imports, or exports.

Usage Context: Indicate where and how this file is utilized within the application (e.g., specific pages, components, or features).

Constraints:

No Suggestions: Do not provide any recommendations for improvements, optimizations, or alternative implementations.

Focus on Description: Concentrate solely on accurately describing the existing code and its role in the application.

File content : """


    # Define the payload (your input prompt)
    payload = {
        "model": "codexpert",  # Replace with the model name you're using
        "messages": [{"role": "user", "content": f"{prompt}\n\n{content}"}]
    }

    try:
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()

        # Process each line of the streamed response
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    response_json = json.loads(line)
                    if "message" in response_json and "content" in response_json["message"]:
                        content = response_json["message"]["content"]
                        if content:  # Only print non-empty content
                            # print(content, end="", flush=True)
                            full_response += content
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
                    print("Raw line:", line)

        return full_response

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")


def get_file_description(file_path: str) -> str:
    """Get file description using AI."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        response = asking_ai(content)


        return response
    except Exception as e:
        return f"Error getting description: {str(e)}"

def process_file(file_path: str, output_dir: str) -> None:
    """Process a single file and save it locally."""
    try:
        # Read the original file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Get file description
        description = get_file_description(file_path)

        # Create the new content with comments
        new_content = f"""# File path: {file_path}
# Description : {description}
# Code:
{content}
"""

        # Create relative path for output file
        relative_path = os.path.relpath(file_path, './repo_optimized')
        output_path = os.path.join(output_dir, relative_path)

        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save the processed file
        with open(f"{output_path}.txt", 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"Processed: {file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")

def count_files_to_process(base_dir: str) -> int:
    """Count the total number of files to process."""
    count = 0
    for root, _, files in os.walk(base_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if not any(skip in file_path for skip in ['.git', 'coverage', 'node_modules', '.DS_Store']):
                count += 1
    return count

def upload_optimized_file():
    """Main function to process all files in the directory and save them locally."""
    # Directory to process
    base_dir = './original_repo'

    # Create output directory
    output_dir = os.path.join(os.path.dirname(base_dir), 'processed_files')
    os.makedirs(output_dir, exist_ok=True)

    # Counter for processed files
    processed_count = 0

    # Walk through the directory with progress bar
    for root, _, files in os.walk(base_dir):
        for file in tqdm(files, desc="Processing files", unit="file"):
            file_path = os.path.join(root, file)
            # Skip binary files and certain directories
            if any(skip in file_path for skip in ['.git', 'coverage', 'node_modules', '.DS_Store']):
                continue
            try:
                 # Count total files to process
                total_files = count_files_to_process(base_dir)
                print(f"\nTotal files to process: {total_files}")
                process_file(file_path, output_dir)
                processed_count += 1
                print(f"\nSuccessfully processed {processed_count} out of {total_files} files")
            except Exception as e:
                print(f"\nFailed to process {file_path}: {str(e)}")



# Example usage
if __name__ == "__main__":
    upload_optimized_file()
