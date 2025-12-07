#!/bin/bash

# Define progress and summary files
progress_file="progress.log"
summary_file="source-control.txt"
main_dir=$(pwd)

# Function to check if a file is already processed
is_processed() {
    grep -Fxq "$1" "$main_dir/$progress_file"
}

# Create logs if missing
touch "$main_dir/$progress_file"
touch "$main_dir/$summary_file"

echo "Script started at $(date)" >> "$main_dir/$progress_file"
echo "Summaries will be saved to $summary_file" >> "$main_dir/$progress_file"

# Summarize a single text file
summarize_file() {
    local file=$1
    local file_name=$(basename "$file")

    # skip if already processed
    if is_processed "$file_name"; then
        return
    fi

    echo "Processing $file_name"
    echo "Processing $file_name" >> "$main_dir/$progress_file"

    # Read first 1000 lines only
    head -n 1000 "$file" > /tmp/first1000.$$  # temp partial copy

    # Write section header in summary file
    echo "### $(basename "$file" .txt)" >> "$main_dir/$summary_file"
    echo "" >> "$main_dir/$summary_file"

    # Summarize those lines
    ollama run granite3.2:8b "Summarize in detail and explain:" < /tmp/first1000.$$ \
        | tee -a "$main_dir/$summary_file"

    echo "" >> "$main_dir/$summary_file"

    rm -f /tmp/first1000.$$

    # Mark file as processed
    echo "$file_name" >> "$main_dir/$progress_file"
}

# Process .txt files in a given directory
process_files() {
    local dir=$1
    echo "Scanning $dir..."
    for file in "$dir"/*.txt; do
        [ -f "$file" ] || continue

        # skip the summary file itself
        if [ "$(basename "$file")" == "$summary_file" ]; then
            continue
        fi

        summarize_file "$file"
    done
}

# Recursively walk directories
process_subdirectories() {
    local parent_dir=$1
    for dir in "$parent_dir"/*/; do
        [ -d "$dir" ] || continue
        process_files "$dir"
        process_subdirectories "$dir"
    done
}

# Run main + recursion
process_files "$main_dir"
process_subdirectories "$main_dir"

echo "Script completed at $(date)" >> "$main_dir/$progress_file"
