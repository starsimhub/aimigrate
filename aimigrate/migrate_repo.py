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
Below is some code for the {library} ({library_alias}) library:

<code>
{library_code}
</code>

Please refactor the code below to be compatible with the {library} library.
Maintain the same style, functionality, and structure as the original code.

<code>
{code}
</code>

Refactored code:
"""

class MigrateRepo(aim.CoreMigrate):

    def __init__(self, source_dir, dest_dir, files=None, # Input and output folders
                 library=None, library_alias=None, v_from=None, v_to=None,  # Migration settings
                 include=None, exclude=None, diff_file=None, diff=None, patience=None, # Diff settings
                 model=None, model_kw=None, base_prompt=None, # Model settings
                 parallel=False, verbose=True, save=True, die=False, run=False): # Run settings
        # Inputs
        self.source_dir = sc.path(source_dir)
        self.dest_dir = sc.path(dest_dir)
        self.files = files
        self.library = library
        self.library_alias = library_alias
        self.v_from = v_from
        self.v_to = v_to
        self.include = sc.ifelse(include, default_include)
        self.exclude = sc.ifelse(exclude, default_exclude)        
        self.diff_file = diff_file
        self.diff = diff
        self.patience = patience                
        self.model = model
        self.model_kw = sc.mergedicts(model_kw)
        self.base_prompt = sc.ifelse(base_prompt, default_base_prompt)
        self.parallel = parallel
        self.verbose = verbose
        self.save = save
        self.die = die

        # Populated fields
        self.chatter = None
        self.encoder = None
        self.code_files = []
        self.errors = []

        # Optionally run
        if run:
            self.run()
        return
            
    def run(self):
        self.make_encoder()
        # get the repository files
        self.get_repo_files()
        # parse the repository files
        self.parse_repo_files()
        # parse the files for migration
        self.make_code_files()
        # make the prompts
        self.make_prompts()
        # run
        self._run()            

    def parse_library(self):
        """ Extract the right folder for library """
        self.log('Parsing library folder')
        if isinstance(self.library, types.ModuleType):
            self.library = sc.thispath(self.library)
        self.library = sc.path(self.library)
        if not self.library.is_dir():
            errormsg = f'The library must be supplied as the module or the folder path, not {self.library}'
            raise FileNotFoundError(errormsg)
        return

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
            code_file.make_prompt(self.base_prompt,
                                  prompt_kwargs = {'library':self.library.stem,
                                                   'library_alias':self.library_alias,
                                                    'library_code':self.repo_string},
                                  encoder=self.encoder)
        return


# class MigrateRepo(aim.Migrate):

#     def make_diff(self):
#         self.get_repo_files()

#     def parse_diff(self):
#         self.parse_repo_files()

#     def get_repo_files(self):
#         self.log("Getting the repository files")
#         self.parse_library()
#         self.repo_files = []
#         all_repo_files = aim.files.get_python_files(self.library, gitignore=True)
#         for current_file in all_repo_files:
#             if self.include and not any(fnmatch.fnmatch(current_file, pattern) for pattern in self.include):
#                 continue
#             elif self.exclude and any(fnmatch.fnmatch(current_file, pattern) for pattern in self.exclude):
#                 continue
#             else:
#                 self.repo_files.append(current_file)

#     def parse_repo_files(self):        
#         self.log("Parsing repository files")
#         self.repo_string = ''
#         for current_file in self.repo_files:
#             with open(self.library / current_file, 'r') as f:
#                 self.repo_string += """FILENAME: {file_name}\n'''python\n {code} '''\n""".format(file_name=current_file, code=f.read())
#         if self.encoder is not None:
#             self.n_tokens = len(self.encoder.encode(self.repo_string))
#         else:
#             self.n_tokens = -1
#         if self.verbose and (self.n_tokens > -1):
#             print(f'Number of tokens in repository files: {self.n_tokens}')        
#         return
    
#     def make_prompts(self):
#         for code_file in self.code_files:
#             code_file.make_prompt(default_base_prompt, self.repo_string, encoder=self.encoder) # HACK: this is a hack to get the code file to have the right prompt string
#         return
