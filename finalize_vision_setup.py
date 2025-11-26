import os
import shutil
import glob

def move_vision_model_files():
    # Define paths
    cache_root = os.path.expanduser("~/.cache/huggingface/hub")
    # The folder name format is models--<org>--<model>
    model_folder_name = "models--kakaocorp--kanana-1.5-v-3b-instruct"
    source_path = os.path.join(cache_root, model_folder_name)
    
    project_root = os.getcwd()
    dest_path = os.path.join(project_root, "model_vision")

    print(f"Looking for model in: {source_path}")

    if not os.path.exists(source_path):
        print("❌ Model folder not found in cache yet. Is the download finished?")
        return

    # Hugging Face stores actual files in 'snapshots/<hash>/'
    snapshots_path = os.path.join(source_path, "snapshots")
    if not os.path.exists(snapshots_path):
        print("❌ Snapshots folder not found.")
        return

    # Get the latest snapshot
    snapshots = os.listdir(snapshots_path)
    if not snapshots:
        print("❌ No snapshots found.")
        return
    
    snapshot_hash = snapshots[0]
    final_source = os.path.join(snapshots_path, snapshot_hash)
    
    print(f"Found snapshot: {snapshot_hash}")
    print(f"Moving files from {final_source} to {dest_path}...")

    # Create destination directory
    if not os.path.exists(dest_path):
        os.makedirs(dest_path)

    # Move files
    try:
        for item in os.listdir(final_source):
            s = os.path.join(final_source, item)
            d = os.path.join(dest_path, item)
            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d)
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        
        print("✅ Files moved successfully!")
        print(f"Vision Model is now located at: {dest_path}")

    except Exception as e:
        print(f"❌ Error moving files: {e}")

if __name__ == "__main__":
    move_vision_model_files()
