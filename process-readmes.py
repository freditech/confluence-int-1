import subprocess
import sys
import os
import re

def get_changed_files():
    """
    Runs git diff to get the list of changed files in the current merge commit.
    Assumes the action checks out the merge commit.
    Compares HEAD (the merge commit) with its first parent (the tip of the
    base branch before the merge).
    """
    try:
        # The command `git diff --name-only HEAD~1 HEAD` compares the state
        # of the repository at the parent of the current commit (HEAD~1)
        # to the state at the current commit (HEAD).
        # In a merge commit triggered by a PR merge, HEAD~1 is the commit
        # on the target branch right before the merge, and HEAD is the
        # merge commit itself. This effectively lists the files changed in the PR.
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
            capture_output=True,
            text=True, # Decode stdout/stderr as text
            check=True # Raise CalledProcessError if the command returns a non-zero exit code
        )
        # Split output into lines and remove any leading/trailing whitespace
        changed_files = result.stdout.strip().splitlines()
        return changed_files
    except subprocess.CalledProcessError as e:
        print(f"Error running git diff: {e}", file=sys.stderr)
        print(f"Stdout:\n{e.stdout}", file=sys.stderr)
        print(f"Stderr:\n{e.stderr}", file=sys.stderr)
        sys.exit(1) # Exit with a non-zero code to indicate failure
    except Exception as e:
        print(f"An unexpected error occurred while getting changed files: {e}", file=sys.stderr)
        sys.exit(1)

def is_readme(filepath):
    """
    Checks if a file path corresponds to a README file.
    Handles common naming conventions and extensions (case-insensitive).
    """
    basename = os.path.basename(filepath).lower()
    # Use a regex to match files starting with 'readme' and optionally
    # having common extensions like .md, .rst, .txt, or no extension.
    # This pattern is more flexible than just checking for .md or .rst.
    # It matches: readme, readme.md, README.txt, Readme.rst, etc.
    # It specifically looks for 'readme' followed by an optional period
    # and then optional characters (like extensions) or the end of the string.
    # It excludes files like 'myreadme.txt'.
    return re.fullmatch(r'readme(\..*)?', basename) is not None


def get_first_line(filepath):
    """
    Reads and returns the first non-empty, non-whitespace line of a file.
    Returns None if the file is empty, doesn't exist, or an error occurs.
    """
    try:
        # Use 'utf-8' encoding, which is common for text files like READMEs
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                stripped_line = line.strip()
                if stripped_line: # Return the first non-empty line
                    return stripped_line
            return "" # Return empty string if file is not found/empty/only whitespace lines
    except FileNotFoundError:
        print(f"Warning: File not found - {filepath}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error reading file {filepath}: {e}", file=sys.stderr)
        return None

def process_first_line(line, filepath):
    """
    Placeholder function to process the first line of a README file.
    Replace this with your actual logic.
    """
    print("-" * 20)
    print(f"Processing first line from: {filepath}")
    print(f"First Line: '{line}'")
    # --- ADD YOUR CUSTOM LOGIC HERE ---
    # For example:
    # - Send the line to another system
    # - Parse the line for specific information
    # - Validate the format of the first line
    # - Trigger another action based on the content
    # some_other_function(line, metadata={'file': filepath})
    print("-" * 20)


def main():
    print("Starting README processing script...")
    changed_files = get_changed_files()

    if not changed_files:
        print("No files reported as changed by git diff.")
        # This might happen in squash merges or if the diff command fails,
        # or genuinely no files were changed (unlikely in a PR merge).
        return

    print(f"Found {len(changed_files)} changed files.")

    readme_files = [f for f in changed_files if is_readme(f)]

    if not readme_files:
        print("No README files were among the changed files.")
        return

    print(f"Processing {len(readme_files)} changed README files:")
    for readme_file in readme_files:
        first_line = get_first_line(readme_file)
        if first_line is not None: # Only process if file was read successfully
            process_first_line(first_line, readme_file)
        else:
            # get_first_line already printed a warning/error message
            pass # Skip processing this file


if __name__ == "__main__":
    main()

