
import base64
import requests
import re
import sys

def main():
    # Read the markdown file
    try:
        with open('data_flow.md', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print("Error: data_flow.md not found in current directory.")
        return

    # Extract mermaid block
    match = re.search(r'```mermaid\n(.*?)\n```', content, re.DOTALL)
    if not match:
        print("Error: No mermaid block found.")
        return
        
    mmd = match.group(1)
    
    # Base64 encode
    graphbytes = mmd.encode("utf8")
    base64_bytes = base64.b64encode(graphbytes)
    base64_string = base64_bytes.decode("ascii")
    
    # Fetch image
    url = "https://mermaid.ink/img/" + base64_string
    print(f"Fetching from {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        output_path = 'data/processed/data_flow.png'
        with open(output_path, 'wb') as f:
            f.write(response.content)
            
        print(f"Success! Image saved to {output_path}")
        
    except Exception as e:
        print(f"Error fetching image: {e}")

if __name__ == "__main__":
    main()
