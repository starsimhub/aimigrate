"""
Migrate out of the box
"""
import aimigrate as aim
import sciris as sc

__all__ = ['MigrateOOB']

default_base_prompt = """
Refactor the code below to work with {library} ({library_alias}). Currently the 
code works with version {v_from} but needs to be updated to work with version {v_to}.
Maintain the same style, functionality, and structure as the original code.

<code>
{code}
</code>

Refactored code:
"""

class MigrateOOB(aim.CoreMigrate):

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

    def make_prompts(self):
        self.make_encoder()
        for code_file in self.code_files:
            code_file.make_prompt(self.base_prompt, 
                                  prompt_kwargs={'library': self.library, 
                                                'library_alias': self.library_alias, 
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
