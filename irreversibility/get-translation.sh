#!/bin/bash

# Define progress and summary files
progress_file="progress.log"
summary_file="translation.txt"
main_dir=$(pwd)

target="$1"

# Function to check if a file is already processed
is_processed() {
    grep -Fxq "$1" "$main_dir/$progress_file"
}

# Create progress and summary files if they don't exist
touch "$main_dir/$progress_file"
touch "$main_dir/$summary_file"

# Start logging script progress
echo "Script started at $(date)" >> "$main_dir/$progress_file"
echo "Summaries will be saved to $summary_file" >> "$main_dir/$progress_file"

# Function to process text files in a directory
process_files() {
    local dir=$1
    local single_file=$2

    echo "Processing directory: $dir"

    # Determine which files to process
    if [ -n "$single_file" ]; then
        files=("$single_file")
    else
        files=("$dir"/*.txt)
    fi

    for file in "${files[@]}"; do
        # Skip if file does not exist (glob safety)
        [ -e "$file" ] || continue

        # Skip processing the summary file
        if [ "$(basename "$file")" = "$summary_file" ]; then
            echo "Skipping summary file: $summary_file"
            continue
        fi

        # Process the file if it's a regular file
        if [ -f "$file" ]; then
            local file_name
            file_name=$(basename "$file")

            # Process only if not processed before
            if ! is_processed "$file_name"; then
                echo "Processing $file_name"
                echo "Processing $file_name" >> "$main_dir/$progress_file"

                # Create a temporary directory for the file's chunks
                sanitized_name=$(basename "$file" | tr -d '[:space:]')
                temp_dir=$(mktemp -d "$dir/tmp_${sanitized_name}_XXXXXX")
                echo "Temporary directory created: $temp_dir" >> "$main_dir/$progress_file"

               # Create coherent sentence-based chunks using Python
		python3 "$main_dir/sentence_chunker.py" < "$file" \
		  | awk '
		    BEGIN {i=0}
		    /^<<<CHUNK>>>$/ {
			i++
			file=sprintf("'"$temp_dir"'/chunk_%03d.txt", i)
			next
		    }
		    {
			print > file
		    }
		  '

                echo "File split into chunks: $(find "$temp_dir" -type f)" >> "$main_dir/$progress_file"

		# Summarize each chunk and append to the summary file
		# Add filename (without .txt) as section header
		echo "### $(basename "$file" .txt)" >> "$main_dir/$summary_file"
		echo "" >> "$main_dir/$summary_file"

		for chunk_file in "$temp_dir"/chunk_*; do
			[ -f "$chunk_file" ] || continue
				echo "Summarizing chunk: $(basename "$chunk_file")"
					ollama run granite3.2:8b "Translate to English:" < "$chunk_file" | tee -a "$main_dir/$summary_file"
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

# Recursively process subdirectories
process_subdirectories() {
	local parent_dir=$1

# Iterate over all subdirectories
		for dir in "$parent_dir"/*/; do
			if [ -d "$dir" ]; then
				process_files "$dir"  # Process files in the subdirectory
					process_subdirectories "$dir"  # Recursive call for nested subdirectories
					fi
					done
}


if [ -n "$target" ]; then
    if [ -f "$target" ]; then
        process_files "$(dirname "$target")" "$target"
        echo "Script completed at $(date)" >> "$main_dir/$progress_file"
        exit 0
    elif [ -d "$target" ]; then
        process_files "$target"
        process_subdirectories "$target"
        echo "Script completed at $(date)" >> "$main_dir/$progress_file"
        exit 0
    else
        echo "Error: target not found: $target"
        exit 1
    fi
fi

process_files "$main_dir"
process_subdirectories "$main_dir"

echo "Script completed at $(date)" >> "$main_dir/$progress_file"


# Mark script completion
echo "Script completed at $(date)" >> "$main_dir/$progress_file"
