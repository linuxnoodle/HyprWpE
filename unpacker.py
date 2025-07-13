import sys
import os
import json
import zipfile

def unpack_pkg(pkg_path, output_dir):
    """
    Unpacks a Wallpaper Engine .pkg file and returns the project.json content.
    """
    if not os.path.exists(pkg_path):
        print(f"Error: File not found at {pkg_path}")
        return None

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(pkg_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
            print(f"Successfully extracted to {output_dir}")

        # Find and parse project.json
        project_json_path = os.path.join(output_dir, 'project.json')
        if os.path.exists(project_json_path):
            with open(project_json_path, 'r') as f:
                return json.load(f)
        else:
            print("Error: project.json not found in the package.")
            return None

    except zipfile.BadZipFile:
        print(f"Error: {pkg_path} is not a valid zip file or is corrupted.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python unpacker.py <path_to_pkg_file> <output_directory>")
        sys.exit(1)
    
    pkg_file = sys.argv[1]
    out_dir = sys.argv[2]
    
    project_data = unpack_pkg(pkg_file, out_dir)
    
    if project_data:
        print("\nProject Details:")
        print(json.dumps(project_data, indent=2))
