import os

# Using a context manager to temporarily change the directory
class TemporaryDirectoryChange:
    def __init__(self, new_dir):
        self.new_dir = new_dir
        self.original_dir = os.getcwd()

    def __enter__(self):
        os.chdir(self.new_dir)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.original_dir)