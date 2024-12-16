"""
Parse the files and folders, including the git diff
"""
import os
import ast
import re
import fnmatch
import tiktoken
import sciris as sc
import starsim_ai as sa
import subprocess


def get_python_files(path, gitignore=False):
    """
    Recursively retrieves all Python files from the specified directory.

    Args:
        path (str): The root directory to search for Python files.

    Returns:
        list: A list of file paths to Python files found within the directory.
    """
    if isinstance(path, str):
        path = sc.path(path)

    if path.suffix == '.py':
        python_files = [path]
    else:
        python_files = []
        if gitignore:
            with sa.utils.TemporaryDirectoryChange(path):
               files = subprocess.check_output("git ls-files", shell=True).splitlines()
               for file in files:
                    decoded = file.decode()
                    if decoded.endswith('.py'):
                         python_files.append(decoded)
        else:
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))
    python_files = [sc.path(file) for file in python_files]
    return python_files


class GitDiff:
    """
    Create and parse the git diff
    """

    def __init__(self, file, include_patterns=None, exclude_patterns=None):

        self.include_patterns = ["*.py"] if include_patterns is None else include_patterns
        self.exclude_patterns = ["docs/*"] if exclude_patterns is None else exclude_patterns

        self.diffs = self.parse_git_diff(file, include_patterns=self.include_patterns, exclude_patterns=self.exclude_patterns)
        return

    def summarize(self):
        """ Summarize the diffs """
        diffs = self.diffs
        print(f"Number of files found: {len(diffs)}")
        print(f"Number of hunks: {sum([len(diff['hunks']) for diff in diffs])}")
        print(f"Names of files found: {[diff['file'] for diff in diffs]}")
        return

    def get_diff_string(self, file=None):
        """ Get the diff string (optionally for a file) """
        if file is not None:
            return ''.join([''.join(diff['hunks']) for diff in self.diffs if diff["file"] == file])
        else:
            return ''.join([''.join(diff['hunks']) for diff in self.diffs])


    def count_all_tokens(self, model="gpt-4o"):
        """ Count the total number of tokens in the diff (all hunks) """
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(self.get_diff_string()))

    def print_file_hunks(self, file):
        """
        Print all hunks for a file
        """
        for diff in self.diffs:
            if diff.file == file:
                print(f"All hunks for {file}")
                for hunk in diff.hunks:
                    print(f"{hunk}\n")
        return

    @staticmethod
    def parse_git_diff(file, include_patterns=None, exclude_patterns=None):
        """
        Parses a git diff file and extracts diffs for specified files, splitting hunks by '@@'.

        Args:
            diff_file_path (str): The path to the diff file.
            patterns (list of str, optional): A list of patterns to filter the files.

        Returns:
            list of dict: A list of dictionaries, each containing the file name and its corresponding diff hunks.
        """
        diffs = []
        current_file = None
        current_hunks = []

        # In case a filename is provided instead of the file contents
        if not isinstance(file, str) or '\n' not in file:
            with open(file, 'r') as f:
                file = f.readlines()

        for line in file.splitlines():
            # Match lines that indicate a new file's diff starts
            file_match = re.match(r'^diff --git a/(.+?) b/', line)
            hunk_start_match = re.match(r'^@@', line)

            if file_match:
                # Save the previous file and hunks if applicable
                if current_file and current_hunks:
                    current_hunks.append(''.join(current_hunks.pop()))
                    diffs.append(sc.objdict({"file": current_file, "hunks": current_hunks}))

                # Start a new file and check if it matches any pattern
                current_file = file_match.group(1)
                if include_patterns and not any(fnmatch.fnmatch(current_file, pattern) for pattern in include_patterns):
                    # Skip files that don't match any include pattern
                    current_file = None
                    current_hunks = []
                elif exclude_patterns and any(fnmatch.fnmatch(current_file, pattern) for pattern in exclude_patterns):
                    # Skip files that match any exclude pattern
                    current_file = None
                    current_hunks = []
                else:
                    current_hunks = []  # Reset hunks for the new file

            elif hunk_start_match:
                # If there's an ongoing hunk, save it as a new entry before starting a new hunk
                if current_file and current_hunks and current_hunks[-1]:
                    current_hunks.append(''.join(current_hunks.pop()))

                # Start a new hunk for the current file
                current_hunks.append([line])

            elif current_hunks:
                # Append line to current hunk if in a hunk
                current_hunks[-1].append(line)

        # Save the last file and hunks if present
        if current_file and current_hunks:
            current_hunks.append(''.join(current_hunks.pop()))
            diffs.append(sc.objdict({"file": current_file, "hunks": current_hunks}))

        return diffs


class PythonCode():
    """
    Parse Python code into classes and methods
    """
    def __init__(self, file_path: str):
        self.code_lines = None
        self.classes = None

        self.from_file(file_path)
        self.set_classes()
        return

    def from_file(self, file_path):
        with open(file_path, 'r') as file:
            self.code_lines = file.readlines()
        return

    def get_code_string(self):
        return ''.join(self.code_lines)

    def set_classes(self):
        tree = ast.parse(''.join(self.code_lines))
        visitor = sa.ClassVisitor()
        visitor.visit(tree)
        self.classes = visitor.classes
        return

    def get_class_methods(self, name):
        # BUG: how does this work for methods with the same name?
        for c in self.classes:
            if c['name'] == name:
                class_code_list = self.code_lines[c['lineno']-1:c['end_lineno']+1]
                tree = ast.parse(''.join(class_code_list))
                visitor = sa.MethodVisitor()
                visitor.visit(tree)
                return class_code_list, visitor
        raise ValueError(f"Class {name} not found")


    def get_class_string(self, name, methods_flag=False):
        if methods_flag:
            code_lines, visitor = self.get_class_methods(name)
            res = {}
            for m in visitor.methods:
                res[m['name']] = ''.join(code_lines[m['lineno']-1:m['end_lineno']+1])
            return res
        else:
            for c in self.classes:
                if c['name'] == name:
                    return ''.join(self.code_lines[c['lineno']-1:c['end_lineno']+1])



