import os
import requests
import time
import random
from urllib.parse import urlparse, parse_qsl
from tkinter import Tk, filedialog

# Function to download images and prompts
def download_images(api_key, model_id, model_version_id, download_folder):
    base_url = "https://civitai.com/api/v1/images"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    params = {
        "limit": 100,
        "modelId": model_id,
        "modelVersionId": model_version_id if model_version_id else None,
        "nsfw": 'X',
        "sort": "Most Reactions"
    }

    # Remove None values from params
    params = {k: v for k, v in params.items() if v is not None}
    next_page_url = None

    while True:
        url = next_page_url if next_page_url else base_url
        response = requests.get(url, headers=headers, params=params if not next_page_url else {})
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            break

        data = response.json()
        items = data.get("items", [])

        if not items:
            print("No more images to download.")
            break

        # Prepare directory
        model_dir = os.path.join(download_folder, str(model_id))
        os.makedirs(model_dir, exist_ok=True)

        if model_version_id:
            model_dir = os.path.join(model_dir, str(model_version_id))
            os.makedirs(model_dir, exist_ok=True)

        for item in items:
            image_url = item.get("url")
            meta = item.get("meta") or {}
            prompt = meta.get("prompt", "No prompt available.")

            if image_url:
                # Extract image filename
                parsed_url = urlparse(image_url)
                image_name = os.path.basename(parsed_url.path)
                image_path = os.path.join(model_dir, image_name)

                # Check if image already exists
                if os.path.exists(image_path):
                    print(f"Image already exists, skipping: {image_name}")
                    continue

                # Download image
                img_response = requests.get(image_url)
                if img_response.status_code == 200:
                    with open(image_path, "wb") as img_file:
                        img_file.write(img_response.content)
                    print(f"Downloaded image: {image_name}")

                    # Save prompt
                    prompt_path = os.path.join(model_dir, f"{os.path.splitext(image_name)[0]}.txt")
                    with open(prompt_path, "w", encoding="utf-8") as prompt_file:
                        prompt_file.write(prompt)
                    print(f"Saved prompt for: {image_name}")
                else:
                    print(f"Failed to download image: {image_url}")

                # Random delay to avoid server blocking
                time.sleep(random.randint(15, 30))

        # Move to next page if available
        next_page_url = data.get("metadata", {}).get("nextPage")
        if not next_page_url:
            break

# Main function to handle user input
def main():
    # Prompt for API key
    api_key = "465064830f1753e0a626ce6b54b8ec13"

    # Select download folder
    Tk().withdraw()
    download_folder = filedialog.askdirectory(title="Select Download Folder")
    if not download_folder:
        print("No folder selected. Exiting.")
        return

    # Prompt for modelId
    model_id = input("Enter the modelId (required): ").strip()
    if not model_id.isdigit():
        print("Invalid modelId. Exiting.")
        return

    # Prompt for modelVersionId
    model_version_id = input("Enter the modelVersionId (optional, press Enter to skip): ").strip()
    if model_version_id and not model_version_id.isdigit():
        print("Invalid modelVersionId. Exiting.")
        return

    # Start downloading
    download_images(api_key, model_id, model_version_id, download_folder)

if __name__ == "__main__":
    main()
