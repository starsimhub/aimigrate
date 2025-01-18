"""
Core classes and functions for ssAI-Migrate
"""
import re
import types
import tiktoken
import sciris as sc
import aimigrate as aim

__all__ = ['CodeFile', 'Migrate', 'migrate']

# TODO: figure out how to expand the context to not need to exclude files
default_include = ["*.py"]
default_exclude = ["__init__.py", "setup.py"]

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
    def __init__(self, source, dest, file, process=True):
        self.source = source
        self.dest = dest
        self.file = file
        self.python_code = None
        self.orig_str = None
        self.prompt = None
        self.chatter = None
        self.n_tokens = None
        self.response = None
        self.new_str = None
        self.error = None
        self.timer = None
        self.cost = {'total': 0, 'prompt': 0, 'completion': 0, 'cost': 0}
        if process:
            self.process_code()
        return

    def process_code(self):
        """ Parse the Python file into a string """
        self.python_code = aim.PythonCode(self.source)
        self.orig_str = self.python_code.get_code_string()
        return

    def make_prompt(self, base_prompt, diff_string, encoder):
        """ Create the prompt for the LLM """
        self.prompt = base_prompt.format(diff_string, self.orig_str)
        self.n_tokens = len(encoder.encode(self.prompt)) # Not strictly needed, but useful to know
        return

    def run_query(self, chatter):
        """ Where everything happens!! """
        with sc.timer(self.file) as self.timer:
            self.response = chatter(self.prompt)
        return self.response

    def parse_response(self):
        """ Extract code from the response object """
        json = self.response.to_json()
        result_string = json['kwargs']['content']
        match_pattern = re.compile(r'```python(.*?)```', re.DOTALL)
        code_match = match_pattern.search(result_string)
        if code_match:
            self.new_str = code_match.group(1)
        else:
            match_pattern = re.compile(r'```(.*?)```', re.DOTALL)
            code_match = match_pattern.search(result_string)
            if code_match:
                self.new_str = code_match.group(1)
            else:
                self.new_str = result_string
        return

    def run(self, chatter, save=True):
        """ Run the migration, using the supplied LLM (chatter) """
        self.run_query(chatter)
        self.parse_response()
        if save:
            self.save()
        return self.response

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
        files (list): if provided, the list of files to migrate (else, migrate all Python files in the source folder)
        library (str/path/module): the library to base the migration on (i.e., Starsim or the path to it)
        v_from (str): the git hash or version of Starsim that the code is currently written in
        v_to (str): the git hash or version of Starsim that the new code should be written in
        diff_file (str): if provided, load this diff file instead of computing it via library/v_from/v_to, i.e. git diff v1.0.3 v2.2.0 > diff_file
        diff (str): if provided, use this diff rather than loading it from file
        model (str): the LLM to use
        model_kw (dict): any keywords to pass to the model
        include (list): the list of files to include from the diff
        exclude (list): the list of files to not include from the diff
        base_prompt (str): the prompt template that will be populated with the diff and file information
        parallel (bool): whether to migrate the files in parallel
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
    def __init__(self, source_dir, dest_dir, files=None, # Input and output folders
                 library=None, v_from=None, v_to=None, diff_file=None, diff=None, # Diff settings
                 model=None, model_kw=None, include=None, exclude=None, base_prompt=None, # Model settings
                 parallel=False, verbose=True, save=True, die=False, run=False, patience=None): # Run settings

        # Inputs
        self.source_dir = sc.path(source_dir)
        self.dest_dir = sc.path(dest_dir)
        self.files = files
        self.library = library
        self.v_from = v_from
        self.v_to = v_to
        self.diff_file = diff_file
        self.diff = diff
        self.model = model
        self.model_kw = sc.mergedicts(model_kw)
        self.include = sc.ifelse(include, default_include)
        self.exclude = sc.ifelse(exclude, default_exclude)
        self.base_prompt = sc.ifelse(base_prompt, default_base_prompt)
        self.parallel = parallel
        self.verbose = verbose
        self.save = save
        self.die = die
        self.patience = patience

        # Populated fields
        self.git_diff = None
        self.encoder = None
        self.chatter = None
        self.code_files = []
        self.errors = []

        # Optionally run
        if run:
            self.run()
        return

    def log(self, string, color='green'):
        """ Print if self.verbose is True """
        if self.verbose:
            printfunc = dict(
                default=print,
                red=sc.printred,
                green=sc.printgreen,
                blue=sc.printcyan
            )[color]
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
            with aim.utils.TemporaryDirectoryChange(self.library):
                self.diff = sc.runcommand(f"git diff {'--patience' if self.patience else None} {self.v_from} {self.v_to}")
        return

    def parse_diff(self, encoding='gpt-4o'):
        """ Parse the diff into the different pieces """
        self.log('Parsing the diff')
        self.git_diff = aim.GitDiff(self.diff, include_patterns=self.include, exclude_patterns=self.exclude)
        self.git_diff.summarize() # summarize
        self.n_tokens = self.git_diff.count_all_tokens(model=encoding) # NB: not implemented for all models
        if self.verbose:
            print(f'Number of tokens {self.n_tokens}')
        return

    def parse_sources(self):
        """ Find the supplied files and parse them """
        self.log('Parsing source files')
        if self.files is None:
            self.files = aim.get_python_files(self.source_dir)
        else:
            self.files = sc.tolist(self.files)

        if not len(self.files):
            errormsg = f'Could not find any Python files to migrate in {self.source_dir}'
            raise FileNotFoundError(errormsg)

        for file in self.files:
            source = self.source_dir / file
            dest = self.dest_dir / file
            code_file = CodeFile(source=source, dest=dest, file=file) # Actually do the processing
            self.code_files.append(code_file)

        return

    def make_chatter(self, encoding='gpt-4o'):
        """ Create the LLM agent """
        self.log('Creating agent...')
        self.encoder = tiktoken.encoding_for_model(encoding) # encoder (for counting tokens)
        self.chatter = aim.SimpleQuery(model=self.model, **self.model_kw)
        return

    def make_prompts(self):
        diff_string = self.git_diff.get_diff_string()
        for code_file in self.code_files:
            code_file.make_prompt(self.base_prompt, diff_string, encoder=self.encoder)
        return

    def run_single(self, code_file):
        """ Where everything happens!! """
        self.log(f'Migrating {code_file.file}: {code_file.n_tokens} tokens')
        try:
            code_file.run(self.chatter, save=self.save)
        except Exception as E:
            errormsg = f'Could not parse {code_file.file}: {E}'
            self.errors.append(errormsg)
            raise E if self.die else print(errormsg)
        return

    def run(self):
        """ Run all steps of the process """
        self.log(f'\nStarting migration of {self.source_dir}', color='blue')
        self.make_diff()
        self.parse_diff()
        self.parse_sources()
        self.make_chatter()
        self.make_prompts()

        self.log(f'\nMigrating {len(self.files)} files', color='blue')
        self.log(f'{sc.newlinejoin(self.files)}', color='default')
        self.timer = sc.timer()
        if self.parallel:
            sc.parallelize(self.run_single, self.code_files, parallelizer='thread')
        else:
            for code_file in self.code_files:
                self.run_single(code_file)
        self.timer.toc('Total time')
        return


def migrate(*args, **kwargs):
    """ Helper function for the Migrate class """
    mig = Migrate(*args, **kwargs)
    mig.run()
    return mig