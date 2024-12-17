"""
Core classes and functions for ssAI-Migrate
"""
import re
import types
import tiktoken
import sciris as sc
import starsim_ai as ssai

__all__ = ['CodeFile', 'Migrate', 'migrate']

# TODO: figure out how to expand the context to not need to exclude files
default_include = ["*.py", "starsim/diseases/sir.py"]
default_exclude = ["starsim/diseases/*", "docs/*", "tests/*", "__init__.py", "setup.py"]

default_base_prompt = '''
Here is the diff information for an update to the starsim (ss) package:
------
{}
------
Please refactor the below code to maintain compatibility with the starsim (ss) code:
------
{}
------
Refactored code:
'''

class CodeFile(sc.prettyobj):
    """
    A class to hold the original and migrated code
    """
    def __init__(self, source, dest, process=True):
        self.source = source
        self.dest = dest
        self.python_code = None
        self.orig_str = None
        self.prompt = None
        self.chatter = None
        self.n_tokens = None
        self.response = None
        self.new_str = None
        self.error = None
        if process:
            self.process_code()
        return
    
    def process_code(self):
        """ Parse the Python file into a string """
        self.python_code = ssai.PythonCode(self.source)
        self.orig_str = self.python_code.get_code_string()
        return
    
    def make_prompt(self, base_prompt, diff_string):
        """ Create the prompt for the LLM """
        self.prompt = base_prompt.format(diff_string, self.orig_str)
        self.n_tokens = len(encoder.encode(self.prompt)) # Not strictly needed, but useful to know
        return
    
    def run_query(self, chatter):
        """ Where everything happens!! """
        self.response = chatter(self.prompt)
        return
    
    def parse_response(self):
        """ Extract code from the response object """
        json = self.response.to_json()
        result_string = json['kwargs']['content']
        match_pattern = re.compile(r'```python(.*?)```', re.DOTALL)
        code_match = match_pattern.search(result_string)
        self.new_str = code_match.group(1)
        return

    def run(self, chatter, save=True):
        """ Run the migration, using the supplied LLM (chatter) """
        self.run_query(chatter)
        self.parse_response()
        if save:
            self.save()
        return

    def save(self):
        """ Write to file """
        sc.makefilepath(self.dest, makedirs=True)
        sc.savetext(self.dest, self.new_str)
        return


class Migrate(sc.prettyobj):
    """
    Handle all steps of code migration

    Args:
        source_dir (str/path): the source folder (or single file) to migrate
        dest_dir (str/path): the destination folder to put the migrated files in
        source_files (list): if provided, the list of files to migrate (else, migrate all Python files in the source folder)
        library (str/path/module): the library to base the migration on (i.e., Starsim or the path to it)
        v_from (str): the git hash or version of Starsim that the code is currently written in
        v_to (str): the git hash or version of Starsim that the new code should be written in
        diff_file (str): if provided, load this diff file instead of computing it via library/v_from/v_to, i.e. git diff v1.0.3 v2.2.0 > diff_file
        diff (str): if provided, use this diff rather than loading it from file
        model (str): the LLM to use
        include (list): the list of files to include from the diff
        exclude (list): the list of files to not include from the diff
        base_prompt (str): the prompt template that will be populated with the diff and file information
        parallel (bool): whether to migrate the files in parallel (not yet implemented)
        verbose (bool): print information during the migration (default True)
        save (bool): whether to save the files to disk (default True)
        run (bool): whether to perform the migration immediately (default False)

    **Example**::

        import starsim as ss
        import starsim_ai as ssai

        M = ssai.Migrate(
            source_dir = '/path/to/your/code/folder', # folder with the code to migrate
            dest_dir = '/path/to/migrated/folder', # folder to output migrated code into
            library = ss, # can also be the path to the starsim folder, which must be the cloned repo (not from pypi)
            v_from = 'v1.0.3', # can be any valid git tag or hash
            v_to = 'v2.2.0', # ditto
            model = 'gpt-4o', # see ssai.Models for list of allowed models
        )
        M.run()
    """
    def __init__(self, source_dir, dest_dir, source_files=None, # Input and output folders
                 library=None, v_from=None, v_to=None, diff_file=None, diff=None, # Diff settings
                 model=None, include=None, exclude=None, base_prompt=None, # Model settings
                 parallel=False, verbose=True, save=True, run=False): # Run settings

        # Inputs
        self.source_dir = sc.path(source_dir)
        self.dest_dir = sc.path(dest_dir)
        self.source_files = source_files
        self.library = library
        self.v_from = v_from
        self.v_to = v_to
        self.diff_file = diff_file
        self.diff = diff
        self.model = model
        self.include = sc.ifelse(include, default_include)
        self.exclude = sc.ifelse(exclude, default_exclude)
        self.base_prompt = sc.ifelse(base_prompt, default_base_prompt)
        self.parallel = parallel
        self.verbose = verbose
        self.save = save

        # Populated fields
        self.git_diff = None
        self.n_tokens = None
        self.code_files = None
        self.encoder = None
        self.chatter = None
        self.errors = []

        # Optionally run
        if run:
            self.run()
        return

    def log(self, string, color='green'):
        """ Print if self.verbose is True """
        if self.verbose:
            printfunc = dict(default=print, red=sc.printred, green=sc.printgreen, blue=sc.printblue)[color]
            printfunc(string)
        return

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

    def make_diff(self):
        """ Handle the different options for the diff: create it, load it, or use it """
        self.log('Making the diff')
        if self.diff:
            return
        elif self.diff_file:
            with open(self.diff_file, 'r') as f:
                self.diff = f.readlines()
        else:
            self.parse_library()
            with ssai.utils.TemporaryDirectoryChange(self.library):
                self.diff = sc.runcommand(f'git diff {self.v_from} {self.v_to}')
        return

    def parse_diff(self, encoding='gpt-4o'):
        """ Parse the diff into the different pieces """
        self.log('Parsing the diff')
        self.git_diff = ssai.GitDiff(self.diff, include_patterns=self.include, exclude_patterns=self.exclude)
        self.git_diff.summarize() # summarize
        self.n_tokens = self.git_diff.count_all_tokens(model=encoding) # NB: not implemented for all models
        if self.verbose:
            print(f'Number of tokens {self.n_tokens}')
        return

    def parse_sources(self):
        """ Find the supplied files and parse them """
        self.log('Parsing source files')
        if self.source_files is None:
            self.source_files = ssai.get_python_files(self.source_dir)
        else:
            self.source_files = sc.tolist(self.source_files)
        
        if not len(self.source_files):
            errormsg = f'Could not find any Python files to migrate in {self.source_dir}'
            raise FileNotFoundError(errormsg)

        for file in self.source_files:
            try:
                source = self.source_dir / file
                dest = self.dest_dir / file
                code_file = CodeFile(source=source, dest=dest) # Actually do the processing
                self.code_files.append(code_file)
            except Exception as E:
                errormsg = f'Could not parse {file}: {E}'
                self.errors.append(errormsg)
                print(errormsg)

        return

    def make_chatter(self, encoding='gpt-4o'):
        """ Create the LLM agent """
        self.log('Creating agent...')
        self.encoder = tiktoken.encoding_for_model(encoding) # encoder (for counting tokens)
        self.chatter = ssai.SimpleQuery(model=self.model)
        return
    
    def make_prompts(self):
        diff_string = self.git_diff.get_diff_string()
        for code_file in self.code_files:
            code_file.make_prompt(self.base_prompt, diff_string, encoder=self.encoder)
        return

    def run_query(self, code_file):
        """ Where everything happens!! """
        response = chatter(prompt)
        return response

    

    def run(self):
        """ Run all steps of the process """
        self.T = sc.timer()
        self.make_diff()
        self.parse_diff()
        self.parse_sources()
        self.make_chatter()
        self.make_prompts()
        self.log(f'Migrating: {self.source_files}')
        for code_string, dest_file in zip(self.code_strings, self.dest_files): # TODO: run in parallel
            self.run_single(code_string, dest_file)
        self.T.toc()
        return


def migrate(*args, **kwargs):
    """ Helper function for the Migrate class """
    mig = Migrate(*args, **kwargs)
    mig.run()
    return mig