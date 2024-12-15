"""
Core classes and functions for ssAI-Migrate
"""
import re
import types
import tiktoken
import sciris as sc
import starsim_ai as ssai

default_include = ["*.py"]
default_exclude = ["docs/*", "__init__.py", "setup.py"]

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


class Migrate:
    """
    Handle all steps of code migration

    Args:
        source (str): the source folder (or single file) to migrate
        dest (str): the destination folder to put the migrated files in
        library (str/Module): the library to base the migration on (i.e., Starsim or the path to it)
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
            source = '/path/to/your/code/folder', # folder with the code to migrate
            dest = '/path/to/migrated/folder', # folder to output migrated code into
            library = ss, # can also be the path to the starsim folder, which must be the cloned repo (not from pypi)
            v_from = 'v1.0.3', # can be any valid git tag or hash
            v_to = 'v2.2.0', # ditto
            model = 'gpt-4o', # see ssai.Models for list of allowed models
        )
        M.run()
    """

    def __init__(self, source, dest=None, library=None, v_from=None, v_to=None, diff_file=None, diff=None,
                 model=None, include=None, exclude=None, base_prompt=None,
                 parallel=False, verbose=True, save=True, run=False):

        # Inputs
        self.source = source
        self.dest = dest
        self.library = library
        self.v_from = v_from
        self.v_to = v_to
        self.diff_fie = diff_file
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
        self.source_files = []
        self.python_codes = []
        self.code_strings = []
        self.prompts = []
        self.responses = []
        self.dest_files = []
        self.errors = []
        self.encoder = None
        self.chatter = None

        # Optionally run
        if run:
            self.run()
        return

    def log(self, string):
        """ Print if self.verbose is True """
        if self.verbose:
            print(string)
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
            with ssai.utils.TemporaryDirectoryChange(self.library):
                self.diff = sc.runcommand(f'git diff {self.v_from} {self.v_to}')
        return

    def parse_diff(self):
        """ Parse the diff into the different pieces """
        self.log('Parsing the diff')
        self.git_diff = ssai.GitDiff(self.diff, include_patterns=self.include, exclude_patterns=self.exclude)
        self.git_diff.summarize() # summarize
        self.n_tokens = self.git_diff.count_all_tokens(model=self.model)
        if self.verbose:
            print(f'Number of tokens {self.n_tokens}')
        return

    def parse_source(self):
        """ Find the supplied files and parse them """
        self.log('Parsing source files')
        self.source_files = ssai.get_python_files(self.source)
        if not len(self.source_files):
            errormsg = f'Could not find any Python files to migrate in {self.source}'
            raise FileNotFoundError(errormsg)

        for file in self.source_files:
            try:
                dest_file = sc.path(self.dest) / file.relative_to(self.source)
                python_code = ssai.PythonCode(file)
                self.python_codes.append(python_code)
                self.code_strings.append(python_code.get_code_string())
                self.dest_files.append(dest_file)
            except Exception as E:
                errormsg = f'Could not parse {file}: {E}'
                self.errors.append(errormsg)

        return

    def make_chatter(self):
        """ Create the LLM agent """
        self.log('Creating agent...')
        self.encoder = tiktoken.encoding_for_model(self.model) # encoder (for counting tokens)
        self.chatter = ssai.SimpleQuery(model=self.model)
        return

    def make_prompt(self, code_string):
        prompt = self.base_prompt.format(self.git_diff.get_diff_string(), code_string)
        self.prompts.append(prompt)
        n_tokens = len(self.encoder.encode(prompt))
        self.log(f"Number of tokens {n_tokens}")
        return prompt

    def run_query(self, prompt):
        self.log('Running query...')
        response = self.chatter(prompt)
        self.responses.append(response)
        return response

    def parse_response(self, response, dest_file):
        self.log('Parsing response...')
        json = response.to_json()
        result_string = json['kwargs']['content']
        match_pattern = re.compile(r'```python(.*?)```', re.DOTALL)
        code_match = match_pattern.search(result_string)
        code = code_match.group(1)

        # Write to file
        if self.save:
            sc.savetext(dest_file, code)
        return

    def run_single(self, code_string, dest_file):
        prompt = self.make_prompt(code_string)
        response = self.run_query(prompt)
        self.parse_response(response, dest_file)
        return

    def run(self):
        """ Run all steps of the process """
        self.T = sc.timer()
        self.parse_starsim()
        self.make_diff()
        self.parse_diff()
        self.parse_source()
        self.make_chatter()
        for code_string, dest_file in zip(self.code_strings, self.dest_files): # TODO: run in parallel
            self.run_single(code_string, dest_file)
        self.T.toc()
        return


def migrate(*args, **kwargs):
    """ Helper function for the Migrate class """
    mig = Migrate(*args, **kwargs)
    mig.run()
    return mig