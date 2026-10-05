import urllib.request
import os
import logging

logging.basicConfig(level=logging.INFO)

def download_video(url, dest_path):
    if os.path.exists(dest_path):
        logging.info(f"File already exists: {dest_path}")
        return
    logging.info(f"Downloading {url} to {dest_path}...")
    try:
        urllib.request.urlretrieve(url, dest_path)
        logging.info(f"Successfully downloaded {dest_path}")
    except Exception as e:
        logging.error(f"Failed to download {url}: {e}")

if __name__ == "__main__":
    out_dir = "eval/data/clips"
    os.makedirs(out_dir, exist_ok=True)
    
    # Intel IoT sample video of factory workers in a zone
    worker_video_url = "https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/master/worker-zone-detection.mp4"
    download_video(worker_video_url, os.path.join(out_dir, "sample_workers.mp4"))
    
    # Another standard sample video of people walking
    people_video_url = "https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/master/person-bicycle-car-detection.mp4"
    download_video(people_video_url, os.path.join(out_dir, "sample_people.mp4"))
    
    # We will use sample_workers.mp4 as our virtual_clip_1 in config
    print("Sample videos downloaded!")
