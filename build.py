import os
import sys
import shutil
import subprocess

APP_NAME = 'vdm'
VERSION = '0.1 beta'
AUTHOR = 'Esther'
DESCRIPTION = 'Virtual Disk Manager'
COPYRIGHT = 'Esther'
URL = 'https://github.com/SterTheStar'
ICON = 'icon.ico'
MAIN_SCRIPT = 'main.py'

PYINSTALLER_ARGS = [
    '--name', APP_NAME,
    '--onefile',
    '--windowed',
    '--add-data', 'main.py:.',
    '--add-data', 'icon.ico:.',
    '--version-file', 'version.txt',
]

def check_pyinstaller():
    try:
        import PyInstaller  # noqa
    except ImportError:
        print('PyInstaller is not installed. Install it with: pip install pyinstaller')
        sys.exit(1)

def write_version_file():
    with open('version.txt', 'w') as f:
        f.write(f"# UTF-8\n")
        f.write(f"CompanyName={AUTHOR}\n")
        f.write(f"FileDescription={DESCRIPTION}\n")
        f.write(f"FileVersion={VERSION}\n")
        f.write(f"LegalCopyright={COPYRIGHT}\n")
        f.write(f"ProductName={APP_NAME}\n")
        f.write(f"ProductVersion={VERSION}\n")
        f.write(f"OriginalFilename={MAIN_SCRIPT}\n")
        f.write(f"Comments={URL}\n")

def build():
    check_pyinstaller()
    write_version_file()
    args = ['pyinstaller', MAIN_SCRIPT]
    args += PYINSTALLER_ARGS
    if os.path.exists(ICON):
        args += ['--icon', ICON]
    print('Running:', ' '.join(args))
    subprocess.run(args, check=True)
    print('\nBuild complete! Check the dist/ folder.')

def clean():
    for folder in ['build', 'dist', '__pycache__']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    for file in ['main.spec', 'version.txt']:
        if os.path.exists(file):
            os.remove(file)
    print('Cleaned build artifacts.')

def usage():
    print('Usage:')
    print('  python build.py build   # Build the VDM app')
    print('  python build.py clean   # Clean build artifacts')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
        sys.exit(0)
    if sys.argv[1] == 'build':
        build()
    elif sys.argv[1] == 'clean':
        clean()
    else:
        usage() 