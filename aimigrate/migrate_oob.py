"""
Migrate out of the box
"""
import aimigrate as aim
import sciris as sc
import types

__all__ = ['MigrateOOB']

DEFAULT_BASE_PROMPT = """
Update the code below to work with {library}{library_alias}. Currently the 
code works with version {v_from} but needs to be updated to work with version {v_to}.
Maintain the same style, functionality, and structure as the original code.

```
{code}
```

Return your updated answer as a single code block embedded between three backticks (```).
"""

class MigrateOOB(aim.CoreMigrate):
    """
    Handle all steps of code migration using an LLM "out of the box".

    Args:
        source_dir (str/path): the source folder (or single file) to migrate
        dest_dir (str/path): the destination folder to put the migrated files in
        files (list): if provided, the list of files to migrate (else, migrate all Python files in the source folder)
        library (str/module): the library to base the migration on
        library_alias (str): string to use as the alias for the library
        v_from (str): the git hash or version of Starsim that the code is currently written in
        v_to (str): the git hash or version of Starsim that the new code should be written in
        model (str): the LLM to use
        model_kw (dict): any keywords to pass to the model
        base_prompt (str): the prompt template that will be populated with the diff and file information
        parallel (bool): whether to migrate the files in parallel
        verbose (bool): print information during the migration (default True)
        save (bool): whether to save the files to disk (default True)
        run (bool): whether to perform the migration immediately (default False)

    **Example**::

        import aimigrate as aim

        M = aim.MigrateOOB(
            source_dir = '/path/to/your/code/folder', # folder with the code to migrate
            dest_dir = '/path/to/migrated/folder', # folder to output migrated code into
            library = ss, # can also be the name of the library as a string (e.g., starsim)
            library_alias = 'ss', # the alias to use for the library in the prompt (optional)
            v_from = 'v1.0', # can be any valid git tag or hash
            v_to = 'v2.0', # ditto
            model = 'gpt-4o', # see aim.Models for list of allowed models
        )
        M.run()
    """
    def __init__(self, source_dir, dest_dir, files=None, # Input and output folders
                 library=None, library_alias=None, v_from=None, v_to=None, # Migration settings
                 model=None, model_kw=None, base_prompt=None, # Model settings
                 parallel=False, verbose=True, save=True, die=False, run=False): # Run setting
        # Inputs
        self.source_dir = sc.path(source_dir)
        self.dest_dir = sc.path(dest_dir)
        self.files = files
        self.library = library
        self.library_alias = library_alias
        self.v_from = v_from
        self.v_to = v_to        
        self.model = model
        self.model_kw = sc.mergedicts(model_kw)
        self.base_prompt = sc.ifelse(base_prompt, DEFAULT_BASE_PROMPT)
        self.parallel = parallel
        self.verbose = verbose
        self.save = save
        self.die = die

        # Populated fields
        self.chatter = None
        self.encoder = None
        self.code_files = []
        self.errors = []

        assert isinstance(self.library, (str, types.ModuleType)), 'Library must be a string or module'

        # Optionally run
        if run:
            self.run()
        return        

    def make_prompts(self):
        self.make_encoder()
        for code_file in self.code_files:
            code_file.make_prompt(self.base_prompt, 
                                  prompt_kwargs={'library': self.library.__name__ if hasattr(self.library, '__name__') else self.library, 
                                                'library_alias': f' ({self.library_alias })'if self.library_alias else '', 
                                                'v_from': self.v_from,
                                                'v_to': self.v_to},
                                                encoder=self.encoder)
    
    def run(self):
        # parse the files for migration
        self.make_code_files()
        # make the prompts
        self.make_prompts()
        # run
        self._run()
