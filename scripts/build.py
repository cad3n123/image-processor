import PyInstaller.__main__
import platform
import os
import shutil
import sys

def build():
    system = platform.system().lower()
    
    # 1. Determine Version
    # If running in GitHub Actions, use the tag name (e.g., "v1.0.0")
    # Otherwise, use "dev-build"
    version = os.environ.get("GITHUB_REF_NAME", "dev-build")
    print(f"🚀 Starting Build for {system} (Version: {version})...")

    # 2. Write version to a file to be bundled
    with open("version.txt", "w") as f:
        f.write(version)

    # 3. Define output name
    if system == "windows":
        out_name = "ProMediaStudio_win"
    elif system == "darwin":
        out_name = "ProMediaStudio_mac"
    else:
        out_name = "ProMediaStudio_linux"

    # 4. PyInstaller Arguments
    # Note: On Windows use ';', on Unix use ':' for add-data separator
    sep = ';' if system == "windows" else ':'
    
    args = [
        'main.py',
        f'--name={out_name}',
        '--onefile',
        '--windowed',
        '--clean',
        # Bundle config and the dynamic version file
        f'--add-data=pixi.toml{sep}.',
        f'--add-data=version.txt{sep}.',
    ]
    
    PyInstaller.__main__.run(args)
    
    # Cleanup version file after build
    if os.path.exists("version.txt"):
        os.remove("version.txt")
        
    print(f"\n✅ Build Complete! Artifact: dist/{out_name}")

if __name__ == "__main__":
    # Ensure we run from project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    # Clean previous builds
    if os.path.exists("dist"): shutil.rmtree("dist")
    if os.path.exists("build"): shutil.rmtree("build")
    
    build()
