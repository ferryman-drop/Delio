
import os
import zipfile
import json
import datetime
import uuid

# Configuration
BACKUP_DIR = "backups"
KERNEL_VERSION = "2.5.0-Phase3"
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
FILENAME = f"delio_kernel_{KERNEL_VERSION}_{TIMESTAMP}.zip"

# Directories to include
INCLUDE_DIRS = [
    "core",
    "states",
    "tools",
    "legacy", # Include legacy for now as we are in transition
    "scripts",
    "config", # Careful with secrets? secrets are in .env usually. config.py is code.
    "docs"
]

# Files to include (Root)
INCLUDE_FILES = [
    "main.py",
    "handlers.py",
    "scheduler.py",
    "requirements.txt",
    "Dockerfile",
    "README.md",
    "init_db.py"
]

# Exclusion Patterns
EXCLUDE_DIRS = [
    "__pycache__",
    ".git",
    "venv",
    "data",
    "backups",
    ".gemini" # Agent data
]

EXCLUDE_EXTENSIONS = [
    ".pyc",
    ".log",
    ".db", # Except schemas? No, don't include DBs.
    ".env", # SECRET
    ".DS_Store"
]

def create_manifest():
    return {
        "version": KERNEL_VERSION,
        "timestamp": datetime.datetime.now().isoformat(),
        "id": str(uuid.uuid4()),
        "description": "Golden Image for Delio Life OS Kernel. Phase 3 Complete.",
        "author": "Antigravity Agent"
    }

def main():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
    zip_path = os.path.join(BACKUP_DIR, FILENAME)
    root_dir = os.getcwd() # Assume run from root
    
    print(f"📦 Freezing Kernel to {zip_path}...")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add Manifest
        manifest = create_manifest()
        zipf.writestr("KERNEL_MANIFEST.json", json.dumps(manifest, indent=2))
        
        # Walk Root Files
        for f in INCLUDE_FILES:
            if os.path.exists(f):
                zipf.write(f, f)
                print(f"  + {f}")
        
        # Walk Dirs
        for d in INCLUDE_DIRS:
            if os.path.exists(d):
                for root, dirs, files in os.walk(d):
                    # Filter Excludes
                    dirs[:] = [wd for wd in dirs if wd not in EXCLUDE_DIRS]
                    
                    for file in files:
                        # Extension check
                        if any(file.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
                            continue
                            
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, file_path)
                        # Minimal log
                        # print(f"  + {file_path}")
                        
    # Verify size
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"✅ Backup Complete. Size: {size_mb:.2f} MB")
    print(f"📁 Location: {zip_path}")

if __name__ == "__main__":
    main()
