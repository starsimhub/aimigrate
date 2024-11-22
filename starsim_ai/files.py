""" files.py
"""
import ast
import re
import fnmatch
import sciris as sc
import starsim_ai as sa

class GitDiff():
    def __init__(self, file_path, include_patterns=None, exclude_patterns=None):

        self.include_patterns = ["*.py"] if include_patterns is None else include_patterns
        self.exclude_patterns = ["docs/*"] if exclude_patterns is None else exclude_patterns

        self.diffs = self.parse_git_diff(file_path, include_patterns=self.include_patterns, exclude_patterns=self.exclude_patterns)

    def summarize(self):
        '''
        Summarize the diffs
        '''
        diffs = self.diffs
        print(f"Number of files found: {len(diffs)}")
        print(f"Number of hunks: {sum([len(diff['hunks']) for diff in diffs])}")
        print(f"Names of files found: {[diff['file'] for diff in diffs]}")

    def print_file_hunks(self, file):
        '''
        Print all hunks for a file
        '''

        for diff in self.diffs:
            if diff["file"] == file:
                print(f"All hunks for {file}")
                for hunk in diff['hunks']:
                    print(f"{hunk}\n")

    @staticmethod
    def parse_git_diff(diff_file_path, include_patterns=None, exclude_patterns=None):
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
        
        with open(diff_file_path, 'r') as file:
            for line in file:
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
    # TODO: deal with functions

    def __init__(self, file_path: str):
        self.code_lines = None
        self.classes = None

        self.from_file(file_path)
        self.set_classes()

    def from_file(self, file_path):
        with open(file_path, 'r') as file:
            self.code_lines = file.readlines()

    def set_classes(self):
        tree = ast.parse(''.join(self.code_lines))
        visitor = sa.ClassVisitor()
        visitor.visit(tree)
        self.classes = visitor.classes

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

    

