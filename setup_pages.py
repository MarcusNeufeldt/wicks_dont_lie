import os
import shutil

# Create pages directory if it doesn't exist
pages_dir = 'pages'
if not os.path.exists(pages_dir):
    os.makedirs(pages_dir)

# Move main.py to pages/1_Main.py
if os.path.exists('main.py'):
    shutil.move('main.py', os.path.join(pages_dir, '1_Main.py'))

print("Pages directory created and files moved successfully!")
