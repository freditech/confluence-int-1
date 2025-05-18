import subprocess
import sys
import os
import re
from atlassian import Confluence
import io # Import io for reading the file content
# import mistune
import markdown
# from md2cf.confluence_renderer import ConfluenceRenderer


# Confluence details (replace with your actual details)

CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
USERNAME = os.environ.get("CONFLUENCE_USER_NAME")
PASSWORD = os.environ.get("CONFLUENCE_USER_PAT")
SPACE_KEY = os.environ.get("CONFLUENCE_SPACE_ID")
PARENT_ID = os.environ.get("CONFLUENCE_PARENT_ID")

# Page details
# page_title = ""
# page_content = "" # HTML or Storage format

# Initialize Confluence API client
confluence = Confluence(
    url=CONFLUENCE_URL,
    username=USERNAME,
    password=PASSWORD
)

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

    process_readme_as_page(line, filepath)

    print("-" * 20)


def get_page_by_title(space_key, title, parent_id):
    """
    Checks if a page with the given title exists in the specified space.
    Returns the page object if found, otherwise returns None.
    """
    try:
        # Use CQL to search for the page by title and space
        cql_query = f'space = "{space_key}" and title = "{title}" and parent = "{parent_id}" and type="page" '
        search_results = confluence.cql(cql_query, expand='version')

        if search_results and 'results' in search_results and len(search_results['results']) > 0:
            # Assuming the first result is the correct page
            found_item = search_results['results'][0]
            if isinstance(found_item, dict) and 'id' in found_item and 'version' in found_item and isinstance(
                    found_item.get('version'), dict) and 'number' in found_item.get('version'):
                # Also explicitly check if the 'type' of the content is 'page'
                return found_item
            else:
                print(
                    f"Warning: Found item with type page and title '{title}' in space '{space_key}' with parent {parent_id} but it does not have the expected structure.",
                    file=sys.stderr)
                # Print the structure for debugging
                print(f"Debug: Found item structure: {found_item}", file=sys.stderr)
                return None
        else:
            return None
    except Exception as e:
        print(f"Error searching for page '{title}' in space '{space_key}': {e}")
        return None


def create_page(space_key, title, body):
    """
    Creates a new page in the specified space.
    Returns the new page object if successful, otherwise returns None.
    """
    try:
        new_page = confluence.create_page(
            space=space_key,
            title=title,
            body=body,
            parent_id=PARENT_ID, # Specify parent_id if creating a sub-page
            representation='storage' # Or 'wiki', 'atlas_doc_format' depending on your content format
        )
        print(f"Page '{title}' created successfully.")
        return new_page
    except Exception as e:
        print(f"Error creating page '{title}' in space '{space_key}': {e}")
        return None


def update_page(page_id, title, body, version):
    """
    Updates an existing page with the given content.
    Requires the page ID, title, new body content, and the current version number.
    Returns the updated page object if successful, otherwise returns None.
    """
    try:
        updated_page = confluence.update_page(
            page_id=page_id,
            title=title,
            body=body,
            version=version,
            representation='storage' # Or 'wiki', 'atlas_doc_format'
        )
        print(f"Page '{title}' (ID: {page_id}) updated successfully.")
        return updated_page
    except Exception as e:
        print(f"Error updating page '{title}' (ID: {page_id}): {e}")
        return None


def read_readme_content(file_path):
    """Reads the content of a file."""
    try:
        with io.open(file_path, mode="r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: README file not found at {file_path}")
        return None
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None


def convert_markdown_to_confluence_storage(markdown_content):
    """
    Converts Markdown content to Confluence Storage Format (XHTML) using md2cf.
    """
    try:
        # md2cf's Publisher can convert markdown to storage format
        # We need a dummy publisher instance to access the conversion method
        # publisher = ConfluencePublisher(
        #     confluence_host=CONFLUENCE_URL,
        #     confluence_username=USERNAME,
        #     confluence_password=PASSWORD, # Or token
        #     confluence_space=SPACE_KEY
        # )
        # Use the internal converter (assuming it's accessible or wrap it)
        # A more direct way if available in the library would be preferable.
        # Looking at md2cf source/docs, it's primarily CLI or requires more setup for library use.
        # A simpler markdown-to-html converter might be a more direct approach if md2cf library usage is complex.
        # Let's use a common markdown to html converter for simplicity if md2cf is hard to use as a library.
        # Searching again for simple markdown to html python library.
        # Using 'markdown' library as a common choice for Markdown to HTML.

        html_content = markdown.markdown(markdown_content)
        # Confluence Storage Format is often HTML wrapped in <ac:structured-macro> or similar,
        # or sometimes just clean HTML is accepted in the 'storage' representation.
        # Let's assume basic HTML from markdown conversion works with 'storage' representation.
        return html_content

    except ImportError:
         print("Error: 'markdown' library not found. Please install it: pip install markdown")
         return None
    except Exception as e:
        print(f"Error converting Markdown to Confluence Storage Format: {e}")
        return None


def get_page_content(readme_file_path):
    readme_content_md = read_readme_content(readme_file_path)
    page_content_storage = None
    if readme_content_md is not None:
        # Convert Markdown to Confluence Storage Format (HTML)
        page_content_storage = convert_markdown_to_confluence_storage(readme_content_md)
    else:
        print("readme content is None. ReadMe might not be found at the specified path.")
    return page_content_storage


# ReadMe <> Page Processing logic
def process_readme_as_page(page_title, readme_file_path):
    existing_page = get_page_by_title(SPACE_KEY, page_title, PARENT_ID)
    page_content = get_page_content(readme_file_path)
    if page_content is not None:
        if existing_page:
            print(f"Page '{page_title}' found. Attempting to update...")
            page_id = existing_page['id']
            current_version = existing_page['version']['number']
            # Increment the version number for the update
            new_version = current_version + 1
            update_page(page_id, page_title, page_content, new_version)
        else:
            print(f"Page '{page_title}' not found. Attempting to create...")
            # Specify parent_id if you want to create this page as a child of another page
            create_page(SPACE_KEY, page_title, page_content)
    else:
        print("Markdown conversion failed. Cannot get page content.")


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
