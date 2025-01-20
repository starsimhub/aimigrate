"""
Migrate using the code in the target as the context.
"""
import re
import types
import fnmatch
import tiktoken
import sciris as sc
import aimigrate as aim

__all__ = ['MigrateRepo']

# TODO: figure out how to expand the context to not need to exclude files
default_include = ["*.py"]
default_exclude = ["__init__.py", "setup.py"]

default_base_prompt = """
Below is the code for the files composing my python module:
<code>
{reference}
</code>

Please refactor the below code to use this module
<code>
{source}
</code>

Refactored code:
"""

class MigrateRepo(aim.Migrate):

    def make_diff(self):
        self.get_repo_files()

    def parse_diff(self):
        self.parse_repo_files()

    def get_repo_files(self):
        self.log("Getting the repository files")
        self.parse_library()
        self.repo_files = []
        all_repo_files = aim.files.get_python_files(self.library, gitignore=True)
        for current_file in all_repo_files:
            if self.include and not any(fnmatch.fnmatch(current_file, pattern) for pattern in self.include):
                continue
            elif self.exclude and any(fnmatch.fnmatch(current_file, pattern) for pattern in self.exclude):
                continue
            else:
                self.repo_files.append(current_file)

    def parse_repo_files(self):        
        self.log("Parsing repository files")
        self.repo_string = ''
        for current_file in self.repo_files:
            with open(self.library / current_file, 'r') as f:
                self.repo_string += """FILENAME: {file_name}\n'''python\n {code} '''\n""".format(file_name=current_file, code=f.read())
        if self.encoder is not None:
            self.n_tokens = len(self.encoder.encode(self.repo_string))
        else:
            self.n_tokens = -1
        if self.verbose and (self.n_tokens > -1):
            print(f'Number of tokens in repository files: {self.n_tokens}')        
        return
    
    def make_prompts(self):
        for code_file in self.code_files:
            code_file.make_prompt(default_base_prompt, self.repo_string, encoder=self.encoder) # HACK: this is a hack to get the code file to have the right prompt string
        return
