import os
import json

workshop_dir = "/home/scushi/.steam/steam/steamapps/workshop/content/431960"

def patch_wallpapers():
    count = 0
    for wid in os.listdir(workshop_dir):
        path = os.path.join(workshop_dir, wid, "project.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except:
                    continue
            
            if data.get('type', '').lower() == 'scene':
                if 'general' not in data:
                    data['general'] = {}
                if 'properties' not in data['general']:
                    data['general']['properties'] = {}
                
                props = data['general']['properties']
                changed = False
                
                # Add dummy properties that commonly cause TypeError in linux-wallpaperengine JS
                for p in ['Player1', 'Player2', 'text']:
                    if p not in props:
                        props[p] = {"type": "text", "value": ""}
                        changed = True
                
                if changed:
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
                    count += 1
                    print(f"Patched {wid}")

if __name__ == "__main__":
    patch_wallpapers()
    print("Done")
