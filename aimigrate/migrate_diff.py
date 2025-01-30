"""
Migrate using diffs
"""
import types
import fnmatch
import sciris as sc
import aimigrate as aim

__all__ = ['MigrateDiff']

# TODO: figure out how to expand the context to not need to exclude files
default_include = ["*.py"]
default_exclude = ["__init__.py", "setup.py"]

default_base_prompt = '''
Here is the diff information for an update to the {library} ({library_alias}) library:
<diff>
{diff}
</diff>

Please refactor the code below to maintain compatibility with the {library} library.
Maintain the same style, functionality, and structure as the original code.

<code>
{code}
</code>

Refactored code:
'''

class MigrateDiff(aim.CoreMigrate):

    def __init__(self, source_dir, dest_dir, files=None, # Input and output folders
                 library=None, library_alias=None, v_from=None, v_to=None,  # Migration settings
                 include=None, exclude=None, diff_file=None, diff=None, patience=None, filter=None, # Diff settings
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
        self.filter = sc.ifelse(filter, [".py"])
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
    
    def make_diff(self):
        self.log('Making the diff')
        if self.diff:
            return
        elif self.diff_file:
            with open(self.diff_file, 'r') as f:
                self.diff = f.readlines()
        else:
            self.parse_library()
            library_files = aim.files.get_python_files(self.library, gitignore=True, filter=self.filter)
            self.diff=''
            with aim.utils.TemporaryDirectoryChange(self.library):
                for current_file in library_files:
                    if self.include and not any(fnmatch.fnmatch(current_file, pattern) for pattern in self.include):
                        continue
                    elif self.exclude and any(fnmatch.fnmatch(current_file, pattern) for pattern in self.exclude):
                        continue
                    else:
                        self.diff += sc.runcommand(f"git diff {'--patience ' if self.patience else ''}{self.v_from} {self.v_to} -- {current_file}")

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
    
    def parse_diff(self):                   
        self.log('Parsing the diff')
        self.git_diff = aim.GitDiff(self.diff, include_patterns=self.include, exclude_patterns=self.exclude)
        self.git_diff.summarize() # summarize
        self.n_tokens = self.git_diff.count_all_tokens(model=self.model) # NB: not implemented for all models
        if self.verbose and (self.n_tokens > -1):
            print(f'Number of tokens in the diff: {self.n_tokens}')      

    def make_prompts(self):
        diff_string = self.git_diff.get_diff_string()
        for code_file in self.code_files:
            code_file.make_prompt(self.base_prompt,
                                  prompt_kwargs = {'library':self.library.stem,
                                                   'library_alias':self.library_alias,
                                                    'diff':diff_string},
                                  encoder=self.encoder)
        return
                
    def run(self):
        # construct the diff
        self.make_diff()
        # parse the diff
        self.parse_diff()
        # parse the files for migration
        self.make_code_files()
        # make the prompts
        self.make_prompts()
        # run
        self._run()    