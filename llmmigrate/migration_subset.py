"""
ssAI-Migrate by identifying a subset of the core to utilize as context
"""
import re
import types
import importlib.util
from pydantic import BaseModel, Field
import sciris as sc
import llmmigrate as mig
import inspect
from pathlib import Path
import traceback


__all__ = ['MigrateWSubset']

default_methods_prompt = """ # In the following Python code, find all dependencies on the {module} package, 
including inherited methods and attributes from parent classes. Return the dependencies without the alias. 
For example: np.sin would becomes numpy.sin
<code>
```python
{code}
```
<answer>
"""
# gets the git diff of a file between two commits
def get_diff(migrator, file):
    """ Handle the different options for the diff: create it, load it, or use it """
    migrator.log('Making the diff')
    migrator.parse_library()
    with mig.utils.TemporaryDirectoryChange(migrator.library):
        result = sc.runcommand(f'git diff {migrator.v_from} {migrator.v_to} -- {file}')
    return result
    
def parse_diffs(migrator, methods_list):
    diffs = {}
    migrator.parse_library()
    if isinstance(migrator.library, types.ModuleType):
        module = migrator.library
    else:
        module = importlib.import_module(migrator.module_name)

    # just keep track of the files that have changes
    for method in methods_list:
        try:
            attr = getattr(module, method)
            attr_file = inspect.getfile(attr)
            trim_length = len(Path(module.__path__[0]).parent.as_posix())
            if attr_file not in diffs:
                stdout = get_diff(migrator, attr_file[trim_length+1:])
                diffs[attr_file] = stdout
        except AttributeError:
            print(f"Attribute {method} not found")
            pass
        except Exception as e:
            print(f"traceback: {traceback.format_exc()}")
            pass
    return diffs        


class CodeFileWSubset(mig.CodeFile):
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
        self.python_code = mig.PythonCode(self.source)
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
        query = mig.CSVQuery(model=migrator.model, **migrator.model_kw)
        # figure out all the module references
        ans = query(default_methods_prompt.format(module=migrator.module_name, code=self.orig_str))
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
    
class MigrateWSubset(mig.Migrate):
    module_name: str = Field(None, description='The name of the module to migrate')

    def set_module_name(self):
        self.parse_library()
        if isinstance(self.library, types.ModuleType):
            self.module_name = self.library.__name__
        else:
            with mig.utils.TemporaryDirectoryChange(self.library):
                module_name = mig.utils.get_module_name()            
            self.module_name = module_name
        return

    def make_prompts(self):
        self.set_module_name()
        for code_file in self.code_files:
            code_file.make_prompt(self.base_prompt, encoder=self.encoder, model=self.model, migrator=self)
        return
        
    def parse_sources(self):
        """ Find the supplied files and parse them """
        self.log('Parsing source files')
        if self.files is None:
            self.files = mig.get_python_files(self.source_dir)
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