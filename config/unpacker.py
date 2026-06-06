import sys
import os
import json
import zipfile
import subprocess
from pathlib import Path

def unpack_pkg(pkg_path, output_dir):
    """
    Unpacks a Wallpaper Engine .pkg file and returns the project.json content if available.
    """
    if not os.path.exists(pkg_path):
        print(f"Error: File not found at {pkg_path}")
        return None

    os.makedirs(output_dir, exist_ok=True)
    extracted = False
    
    # Try RePKG extraction first via dotnet
    repkg_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RePKG.exe')
    if os.path.exists(repkg_exe):
        try:
            print(f"Trying RePKG.exe extraction on {pkg_path}...")
            cmd = ['dotnet', repkg_exe, 'extract', pkg_path, '-o', output_dir, '--overwrite']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Successfully extracted with RePKG.exe to {output_dir}")
                extracted = True
            else:
                print(f"RePKG.exe failed with exit code {result.returncode}:\n{result.stderr}\n{result.stdout}")
                print("Falling back to zipfile...")
        except Exception as e:
            print(f"Exception running RePKG.exe: {e}")
    
    # Fallback to ZipFile
    if not extracted:
        try:
            with zipfile.ZipFile(pkg_path, 'r') as zip_ref:
                zip_ref.extractall(output_dir)
                print(f"Successfully extracted with zipfile to {output_dir}")
                extracted = True
        except zipfile.BadZipFile:
            print(f"Error: {pkg_path} is not a valid zip file or is corrupted.")
        except Exception as e:
            print(f"An error occurred during zipfile extraction: {e}")
            
    if not extracted:
        return None

    # Find and parse project.json
    project_json_path = os.path.join(output_dir, 'project.json')
    if os.path.exists(project_json_path):
        with open(project_json_path, 'r') as f:
            return json.load(f)
    else:
        print("Note: project.json not found in the package (normal for scenes).")
        return {}

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python unpacker.py <path_to_pkg_file> <output_directory>")
        sys.exit(1)
    
    pkg_file = sys.argv[1]
    out_dir = sys.argv[2]
    
    project_data = unpack_pkg(pkg_file, out_dir)
    
    if project_data is not None:
        if project_data:
            print("\nProject Details:")
            print(json.dumps(project_data, indent=2))
        else:
            print("\nExtraction completed (no project.json inside).")
