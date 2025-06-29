#!/bin/bash

# Define progress and summary files
progress_file="progress.log"
summary_file="prospectus.txt"
overview_file="prospectus-overview.txt"
main_dir=$(pwd)

# Function to check if a file is already processed
is_processed() {
    grep -Fxq "$1" "$main_dir/$progress_file"
}

# Create progress, summary, and overview files if they don't exist
touch "$main_dir/$progress_file"
touch "$main_dir/$summary_file"
touch "$main_dir/$overview_file"

# Start logging script progress
echo "Script started at $(date)" >> "$main_dir/$progress_file"
echo "Summaries will be saved to $summary_file" >> "$main_dir/$progress_file"
echo "Overview will be saved to $overview_file" >> "$main_dir/$progress_file"

# Function to process text files in a directory for summaries
process_files_for_summary() {
    local dir=$1
    echo "Processing directory for summaries: $dir"
    
    # Iterate over each .txt file in the specified directory
    for file in "$dir"/*.txt; do
        # Skip if no .txt files are found
        if [ ! -e "$file" ]; then
            continue
        fi

        # Skip processing the summary and overview files
        if [ "$(basename "$file")" == "$summary_file" ] || [ "$(basename "$file")" == "$overview_file" ]; then
            echo "Skipping file: $(basename "$file")"
            continue
        fi

        # Process the file if it's a regular file
        if [ -f "$file" ]; then
            local file_name=$(basename "$file")  # Get the file name only
            
            # Process only if not processed before
            if ! is_processed "$file_name"; then
                echo "Processing $file_name"
                echo "Processing $file_name" >> "$main_dir/$progress_file"

                # Create a temporary directory for the file's chunks
                sanitized_name=$(basename "$file" | tr -d '[:space:]')
                temp_dir=$(mktemp -d "$dir/tmp_${sanitized_name}_XXXXXX")
                echo "Temporary directory created: $temp_dir" >> "$main_dir/$progress_file"

                # Split the file into chunks of 250 lines each
                split -l 250 "$file" "$temp_dir/chunk_"
                echo "File split into chunks: $(find "$temp_dir" -type f)" >> "$main_dir/$progress_file"

                # Summarize each chunk and append to the summary file
                # Add filename (without .txt) as section header
                echo "### $(basename "$file" .txt)" >> "$main_dir/$summary_file"
                echo "" >> "$main_dir/$summary_file"

                for chunk_file in "$temp_dir"/chunk_*; do
                    [ -f "$chunk_file" ] || continue
                    echo "Summarizing chunk: $(basename "$chunk_file")"
                    ollama run granite3.2:8b "Summarize in detail and explain:" < "$chunk_file" | tee -a "$main_dir/$summary_file"
                    echo "" >> "$main_dir/$summary_file"
                done

                # Remove the temporary directory
                rm -rf "$temp_dir"
                echo "Temporary directory $temp_dir removed" >> "$main_dir/$progress_file"

                # Mark the file as processed
                echo "$file_name" >> "$main_dir/$progress_file"
            fi
        fi
    done
}

# Function to process text files in a directory for overview
process_files_for_overview() {
    local dir=$1
    echo "Processing directory for overview: $dir"
    
    # Initialize temporary file for combining all .txt files in the directory
    combined_file=$(mktemp "$dir/combined_XXXXXX.txt")
    
    # Iterate over each .txt file in the specified directory
    for file in "$dir"/*.txt; do
        # Skip if no .txt files are found
        if [ ! -e "$file" ]; then
            continue
        fi

        # Skip processing the summary and overview files
        if [ "$(basename "$file")" == "$summary_file" ] || [ "$(basename "$file")" == "$overview_file" ]; then
            echo "Skipping file: $(basename "$file")"
            continue
        fi

        # Process the file if it's a regular file
        if [ -f "$file" ]; then
            # Append file content to combined file
            cat "$file" >> "$combined_file"
        fi
    done

    # Create overview from combined file if it contains data
    if [ -s "$combined_file" ]; then
        echo "Creating overview for directory: $dir"
        echo "### Overview for $dir" >> "$main_dir/$overview_file"
        echo "" >> "$main_dir/$overview_file"
        # Split the combined file into chunks of 3000 lines
        temp_dir=$(mktemp -d "$dir/tmp_combined_XXXXXX")
        split -l 3000 "$combined_file" "$temp_dir/chunk_"
        for chunk_file in "$temp_dir"/chunk_*; do
            [ -f "$chunk_file" ] || continue
            echo "Summarizing chunk for overview: $(basename "$chunk_file")"
            ollama run granite3.2:8b "Provide an overview of the following content:" < "$chunk_file" | tee -a "$main_dir/$overview_file"
            echo "" >> "$main_dir/$overview_file"
        done
        # Remove the temporary directory
        rm -rf "$temp_dir"
    fi

    # Remove the combined file
    rm -f "$combined_file"
}

# Recursively process subdirectories
process_subdirectories() {
    local parent_dir=$1

    # Iterate over all subdirectories
    for dir in "$parent_dir"/*/; do
        if [ -d "$dir" ]; then
            process_files_for_summary "$dir"  # Process files in the subdirectory for summaries
            process_files_for_overview "$dir"  # Process files in the subdirectory for overview
            process_subdirectories "$dir"  # Recursive call for nested subdirectories
        fi
    done
}

# Main execution
process_files_for_summary "$main_dir"  # Process files in the main directory for summaries
process_files_for_overview "$main_dir"  # Process files in the main directory for overview
process_subdirectories "$main_dir"  # Process files in subdirectories

# Mark script completion
echo "Script completed at $(date)" >> "$main_dir/$progress_file"