"""
ssAI-Migrate by identifying a subset of the core to utilize as context
"""
import re
from pydantic import BaseModel, Field
import sciris as sc
import starsim as ss
import starsim_ai as ssai
import inspect
import subprocess

__all__ = ['MigrateWSubset']

default_methods_prompt = """
In the following Python code, find all dependencies on the {} package, 
including inherited methods and attributes from parent classes. Do not list starsim or ss itself.
List only the dependencies from starsim.
-------------
Here is an example:

Code:
```python
import starsim as ss

# Define the parameters
pars = dict(
    n_agents = 5_000,     # Number of agents to simulate
    networks = dict(      # Networks define how agents interact w/ each other
        type = 'random',  # Here, we use a 'random' network
        n_contacts = 10   # Each person has 10 contacts with other people
    ),
    diseases = dict(      # *Diseases* add detail on what diseases to model
        type = 'sir',     # Here, we're creating an SIR disease
        init_prev = 0.01, # Proportion of the population initially infected
        beta = 0.05,      # Probability of transmission between contacts
    )
)

# Make the sim, run and plot
sim = ss.Sim(pars)
sim.run()
sim.plot() # Plot all the sim results
sim.diseases.sir.plot() # Plot the standard SIR curves
```
Answer:
['ss.Sim', 'ss.Sim.run', 'ss.Sim.plot', 'ss.diseases', 'ss.diseases.sir', 'ss.diseases.sir.plot']
-------------

Now, it's  your turn. Please be as accurate as possible.

Code:

```python
{}
```

Answer:
"""

# gets the git diff of a file between two commits
def get_diff(migrator, file):
    with ssai.utils.TemporaryDirectoryChange(migrator.library):
        cmd = [s for s in f"git diff {migrator.v_from} {migrator.v_to} -- {file}".split()]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=migrator.library)
    return result.stdout

def parse_diffs(migrator, methods_list):
    diffs = {}
    # just keep track of the files that have changes
    for method in methods_list:
        if method.startswith("ss."):
            method_str = method.split("ss.", 1)[1]
        else:
            method_str = method
        try:
            attr = getattr(ss, method_str)
            attr_file = inspect.getfile(attr)
            if attr_file not in diffs:
                stdout = get_diff(migrator, attr_file)
                diffs[attr_file] = stdout
        except AttributeError:
            # print(f"Attribute {method_str} not found")
            pass
        except Exception as e:
            # print(f"traceback: {traceback.format_exc()}")
            pass
    return diffs        


class CodeFileWSubset(ssai.CodeFile):
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
        if process:
            self.process_code()
        return

    def process_code(self):
        """ Parse the Python file into a string """
        self.python_code = ssai.PythonCode(self.source)
        self.orig_str = self.python_code.get_code_string()
        return


    def make_prompt(self, base_prompt, encoder, model, migrator):
        """ Create the prompt for the LLM """
        methods_list = self.parse_methods(migrator=migrator)
        diffs = parse_diffs(migrator, methods_list=methods_list)
        self.prompt = base_prompt.format("\n".join(diffs.values()), self.orig_str)
        self.n_tokens = len(encoder.encode(self.prompt)) # Not strictly needed, but useful to know
        return

    def parse_methods(self, migrator):
        # query format is CSV
        query = ssai.CSVQuery(model=migrator.model, **migrator.model_kw)
        # figure out all the references to starsim
        ans = query(default_methods_prompt.format("starsim (ss)", self.orig_str))
        ans = [a.replace('`', '') for a in ans] # remove backticks
        return ans
    
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
        self.new_str = code_match.group(1)
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
    
class MigrateWSubset(ssai.Migrate):

    def make_prompts(self):
        for code_file in self.code_files:
            code_file.make_prompt(self.base_prompt, encoder=self.encoder, model=self.model, migrator=self)
        return
        
    def parse_sources(self):
        """ Find the supplied files and parse them """
        self.log('Parsing source files')
        if self.files is None:
            self.files = ssai.get_python_files(self.source_dir)
        else:
            self.files = sc.tolist(self.files)

        if not len(self.files):
            errormsg = f'Could not find any Python files to migrate in {self.source_dir}'
            raise FileNotFoundError(errormsg)

        for file in self.files:
            source = self.source_dir / file
            dest = self.dest_dir / file
            code_file = CodeFileWSubset(source=source, dest=dest, file=file) # Actually do the processing
            self.code_files.append(code_file)

        return