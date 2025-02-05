"""
Migrate using the code in the target libarary as context.
"""

import fnmatch
import sciris as sc
import aimigrate as aim

__all__ = ["MigrateRepo"]

# TODO: figure out how to expand the context to not need to exclude files
DEFAULT_INCLUDE = ["*.py"]
DEFAULT_EXCLUDE = ["__init__.py", "setup.py"]

DEFAULT_BASE_PROMPT = """
Below is some code for the {library}{library_alias} library:

```
{library_code}
```

Please update the code below to be compatible with the {library} library.
Maintain the same style, functionality, and structure as the original code.

```
{code}
```

Return your updated answer as a single code block embedded between three backticks (```).
"""


class MigrateRepo(aim.CoreMigrate):
    """
    Handle all steps of code migration using files (e.g., code) from the target library as context.

    Args:
        source_dir (str/path): the source folder (or single file) to migrate
        dest_dir (str/path): the destination folder to put the migrated files in
        files (list): if provided, the list of files to migrate (else, migrate all Python files in the source folder)
        library (str/path/module): the library to base the migration on (i.e., the path to a git repository)
        library_alias (str): string to use as the alias for the library
        v_from (str): the git hash or version of Starsim that the code is currently written in
        v_to (str): the git hash or version of Starsim that the new code should be written in
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

        import aimigrate as aim

        M = aim.MigrateRepo(
            source_dir = '/path/to/your/code/folder', # folder with the code to migrate
            dest_dir = '/path/to/migrated/folder', # folder to output migrated code into
            library = ss, # can also be the path to the starsim folder, which must be the cloned repo (not from pypi)
            library_alias = 'ss', # the alias to use for the library in the prompt (optional)
            v_from = 'v1.0', # can be any valid git tag or hash
            v_to = 'v2.0', # ditto
            model = 'openai:gpt-4o', # use aisuite's provider:model syntax
        )
        M.run()
    """

    def __init__(
        self,
        source_dir,
        dest_dir,
        files=None,  # Input and output folders
        library=None,
        library_alias=None,
        v_from=None,
        v_to=None,
        filter=None,  # Migration settings
        include=None,
        exclude=None,  # Library settings
        model=None,
        model_kw=None,
        base_prompt=None,  # Model settings
        parallel=False,
        verbose=True,
        save=True,
        die=False,
        run=False,
    ):  # Run settings
        # Inputs
        self.source_dir = sc.path(source_dir)
        self.dest_dir = sc.path(dest_dir)
        self.files = files
        self.library = library
        self.library_alias = library_alias
        self.v_from = v_from
        self.v_to = v_to
        self.include = sc.ifelse(include, DEFAULT_INCLUDE)
        self.exclude = sc.ifelse(exclude, DEFAULT_EXCLUDE)
        self.model = model
        self.model_kw = sc.mergedicts(model_kw)
        self.base_prompt = sc.ifelse(base_prompt, DEFAULT_BASE_PROMPT)
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

    def get_repo_files(self):
        self.log("Getting the repository files")
        self.parse_library()
        self.repo_files = []
        with aim.utils.TemporaryDirectoryChange(self.library):
            # get current git commit
            current_head = sc.runcommand("git rev-parse HEAD")
            assert not sc.runcommand(f"git checkout {self.v_to}").startswith("error"), (
                "Invalid v_to"
            )
            all_repo_files = aim.files.get_python_files(
                self.library, gitignore=True, filter=self.filter
            )
            assert not sc.runcommand(f"git checkout {current_head}").startswith(
                "error"
            ), "Error checking out previous commit"
        for current_file in all_repo_files:
            if self.include and not any(
                fnmatch.fnmatch(current_file, pattern) for pattern in self.include
            ):
                continue
            elif self.exclude and any(
                fnmatch.fnmatch(current_file, pattern) for pattern in self.exclude
            ):
                continue
            else:
                self.repo_files.append(current_file)

    def parse_repo_files(self):
        self.log("Parsing repository files")
        self.repo_string = ""
        for current_file in self.repo_files:
            with open(self.library / current_file, "r") as f:
                self.repo_string += """File: {file_name}\n'''\n {code} '''\n""".format(
                    file_name=current_file, code=f.read()
                )
        if self.encoder is not None:
            self.n_tokens = len(self.encoder.encode(self.repo_string))
        else:
            self.n_tokens = -1
        if self.verbose and (self.n_tokens > -1):
            print(f"Number of tokens in repository files: {self.n_tokens}")
        return

    def make_prompts(self):
        for code_file in self.code_files:
            code_file.make_prompt(
                self.base_prompt,
                prompt_kwargs={
                    "library": self.library.stem,
                    "library_alias": f" ({self.library_alias})"
                    if self.library_alias
                    else "",
                    "library_code": self.repo_string,
                },
                encoder=self.encoder,
            )
        return
