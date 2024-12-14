"""
Core classes and functions for ssAI-Migrate

import starsim as ss
import starsim_ai as ssai

mig = ssai.Migrate(
    source = '/path/to/your/code/folder', # folder with the code to migrate
    dest = '/path/to/migrated/folder', # folder to output migrated code into
    starsim = ss, # can also be the path to the starsim folder, which must be the cloned repo (not from pypi)
    v_from = 'v1.0.3', # can be any valid git tag or hash
    v_to = 'v2.2.0',
    model = 'gpt-4o', # see ssai.model_options for list of allowed models
)
mig.run()
"""
import re
import types
import tiktoken
import sciris as sc
import starsim_ai as ssai


class Migrate:

    def __init__(self, source, dest, starsim=None, v_from=None, v_to=None, diff_file=None, diff=None,
                 model=None, include=None, exclude=None,
                 prompt_start=None, prompt_mid=None, prompt_end=None,
                 verbose=True, run=False):
        self.source = source
        self.dest = dest
        self.starsim = starsim
        self.v_from = v_from
        self.v_to = v_to
        self.diff_file = diff_file
        self.diff = diff
        self.model = model
        self.verbose = verbose
        if run:
            self.run()
        return

    def parse_starsim(self):
        """ Extract the right folder for Starsim """
        if isinstance(self.starsim, types.ModuleType):
            self.starsim = sc.thispath(self.starsim)
        self.starsim = sc.path(self.starsim)
        if not self.starsim.is_dir():
            errormsg = f'Starsim must be supplied as the module or the folder path, not {self.starsim}'
            raise FileNotFoundError(errormsg)
        return

    def make_diff(self):
        """ Handle the different options for the diff: create it, load it, or use it """
        if self.diff:
            return
        elif self.diff_file:



    def parse_diff(self):
        """ Parse the diff into the different pieces """
        kjdf

    def parse_code(self):
        kjdf

    def run_query(self):
        pass

    def parse_response(self):
        pass

    def execute(self):
        kjdf

    def run(self):
        """ Run all steps of the process """
        self.parse_starsim()
        self.make_diff()
        self.parse_diff()
        self.parse_code()
        for code_string in self.code_strings:
            self.execute(code_string)
        return





def migrate(*args, **kwargs):
    """ Helper function for the Migrate class """
    mig = Migrate(*args, **kwargs)
    mig.run()
    return mig


def migrate():

    code_file = sc.path(code_file)

    # class for parsing the diff
    include_patterns = ["*.py", "starsim/diseases/sir.py"]; exclude_patterns = ["docs/*", "starsim/__init__.py", "starsim/diseases/*", "setup.py", "tests/*"] # Number of tokens 113743
    git_diff = ssai.GitDiff(self.diff, include_patterns=include_patterns, exclude_patterns=exclude_patterns)
    git_diff.summarize() # summarize
    if report_token_count:
        print(f'Number of tokens {git_diff.count_all_tokens(model=model)}')

    # class for parsin the code
    python_code = ssai.PythonCode(code_file)

    # chatter
    chatter = ssai.SimpleQuery(model=model)

    # encoder (for counting tokens)
    encoder = tiktoken.encoding_for_model("gpt-4o") # CK: or "model"?

    # the prompt template
    prompt_template = '''
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

    # refactor the entire code chunk
    code_string = python_code.get_code_string()

    prompt = prompt_template.format(git_diff.get_diff_string(), code_string) # Number of tokens 60673
    n_tokens = len(encoder.encode(prompt))
    if report_token_count:
        print(f"Number of tokens {n_tokens}")

    # Do the thing! ($$)
    response = chatter(prompt)

    # Extract the result
    json = response.to_json()
    result_string = json['kwargs']['content']
    match_pattern = re.compile(r'```python(.*?)```', re.DOTALL)
    code_match = match_pattern.search(result_string)
    code = code_match.group(1)

    # Write to file
    outfile = f"{out_dir}/{code_file}"
    sc.savetext(outfile, code)

    return n_tokens


if __name__ == "__main__":

    # Settings
    models = ['gpt-4o-mini', 'gpt-4o', 'gemini-1.5-flash', 'gemini-1.5-flash-8b']

    # Do the migration
    T = sc.timer()

    migrate(
        code_file = 'typhoidsim/environment.py',
        model = models[1],
    )

    T.toc()
