import os
import shutil
from huggingface_hub import hf_hub_download, HfApi

def download_repo_pt_files(repo_id, out_dir, target_filename=None, save_as=None):
    api = HfApi()
    files = api.list_repo_files(repo_id=repo_id)
    
    pt_files = [f for f in files if f.endswith(".pt")]
    
    if target_filename and target_filename in pt_files:
        pt_files = [target_filename]
    elif not pt_files:
        print(f"No .pt files found in {repo_id}")
        return None
    
    file_to_download = pt_files[0]
    print(f"Downloading {file_to_download} from {repo_id}...")
    
    os.makedirs(out_dir, exist_ok=True)
    local_path = hf_hub_download(repo_id=repo_id, filename=file_to_download, local_dir=out_dir)
    
    if save_as:
        new_path = os.path.join(out_dir, save_as)
        shutil.move(local_path, new_path)
        local_path = new_path
        
    print(f"Saved to {local_path}\n")
    return local_path

if __name__ == "__main__":
    out_dir = "models"
    
    # 1. Primary PPE
    download_repo_pt_files("Hexmon/vyra-yolo-ppe-detection", out_dir, save_as="ppe_primary.pt")
    
    # 2. Challenger PPE
    download_repo_pt_files("ayushgupta7777/safetyvision-yolov8", out_dir, "v2/best.pt", save_as="ppe_challenger.pt")
    
    # 3. Primary Fire/Smoke
    download_repo_pt_files("rabahdev/fire-smoke-yolov8n", out_dir, "best.pt", save_as="fire_primary.pt")
    
    print("All weights cached successfully!")
