import os
import importlib.util

# Using a context manager to temporarily change the directory
class TemporaryDirectoryChange:
    """
    A context manager to temporarily change the current working directory.

    Example:
    ```python
    with TemporaryDirectoryChange('/path/to/new/dir'):
        # Code that runs in the new directory
        pass
    ```

    Attributes:
        new_dir (str): The directory to change to.
        original_dir (str): The original directory before the change.

    Methods:
        __enter__(): Changes the current working directory to `new_dir`.
        __exit__(exc_type, exc_value, traceback): Reverts the current working directory to `original_dir`.
    """
    def __init__(self, new_dir):
        self.new_dir = new_dir
        self.original_dir = os.getcwd()

    def __enter__(self):
        os.chdir(self.new_dir)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.original_dir)


class EmptyCallback:
    """
    A context manager that does nothing when it is called.

    Example:
    ```python
    with EmptyCallback() as callback:
        # Code that runs without any effect from the callback
        pass
    ```
    """
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


def get_module_name():
    current_dir = os.path.abspath(os.getcwd())
    parent_dir = os.path.dirname(current_dir)
    module_name = os.path.basename(current_dir)

    # Check if the module or package can be imported
    spec = importlib.util.find_spec(module_name, [parent_dir])
    if spec is not None:
        return module_name
    else:
        return None
    
#