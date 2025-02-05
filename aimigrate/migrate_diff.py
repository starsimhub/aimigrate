"""
Migrate using diffs
"""

import fnmatch
import sciris as sc
import aimigrate as aim

__all__ = ["MigrateDiff"]

# TODO: figure out how to expand the context to not need to exclude files
DEFAULT_INCLUDE = ["*.py"]
DEFAULT_EXCLUDE = ["__init__.py", "setup.py"]

DEFAULT_BASE_PROMPT = """
Here is the information for an update to the {library}{library_alias} library captured in a git diff:

```
{diff}
```

Please update the code below to maintain compatibility with the {library} library.
Maintain the same style, functionality, and structure as the original code.

```
{code}
```

Return your updated answer as a single code block embedded between three backticks (```).
"""


class MigrateDiff(aim.CoreMigrate):
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
        diff_speed (bool): whether to use include/exclude to choose files for diff construction. (default False)
        filter (list): if diff_speed=True, a list of file extensions to include when constructing the diff (default [".py"])
        parallel (bool): whether to migrate the files in parallel
        verbose (bool): print information during the migration (default True)
        save (bool): whether to save the files to disk (default True)
        run (bool): whether to perform the migration immediately (default False)

    **Example**::

        import starsim as ss
        import starsim_ai as ssai

        M = aim.Migrate(
            source_dir = '/path/to/your/code/folder', # folder with the code to migrate
            dest_dir = '/path/to/migrated/folder', # folder to output migrated code into
            library = ss, # can also be the path to the starsim folder, which must be the cloned repo (not from pypi)
            v_from = 'v1.0.3', # can be any valid git tag or hash
            v_to = 'v2.2.0', # ditto
            model = 'gpt-4o', # see aim.Models for list of allowed models
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
        v_to=None,  # Migration settings
        include=None,
        exclude=None,
        diff_file=None,
        diff=None,
        patience=None,
        diff_speed=False,
        filter=None,  # Diff settings
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
        self.diff_file = diff_file
        self.diff = diff
        self.patience = patience
        self.model = model
        self.model_kw = sc.mergedicts(model_kw)
        self.base_prompt = sc.ifelse(base_prompt, DEFAULT_BASE_PROMPT)
        self.filter = sc.ifelse(filter, [".py"])
        self.diff_speed = diff_speed
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
        self.log("Making the diff")
        if self.diff:
            return
        elif self.diff_file:
            with open(self.diff_file, "r") as f:
                self.diff = f.readlines()
        else:
            self.parse_library()
            if self.diff_speed:
                self.diff = ""
                with aim.utils.TemporaryDirectoryChange(self.library):
                    # check that the revisions are good
                    assert not sc.runcommand(
                        f"git rev-parse --verify {self.v_from}"
                    ).startswith("fatal"), "Invalid v_from"
                    assert not sc.runcommand(
                        f"git rev-parse --verify {self.v_to}"
                    ).startswith("fatal"), "Invalid v_to"
                    # get current git commit
                    current_head = sc.runcommand("git rev-parse HEAD")
                    # get the files in the library
                    library_files = aim.files.get_python_files(
                        self.library, gitignore=True, filter=self.filter
                    )
                    assert not sc.runcommand(f"git checkout {current_head}").startswith(
                        "error"
                    ), "Error checking out previous commit"
                    # get the diff for each file that passes the include/exclude
                    for current_file in library_files:
                        if self.include and not any(
                            fnmatch.fnmatch(current_file, pattern)
                            for pattern in self.include
                        ):
                            continue
                        elif self.exclude and any(
                            fnmatch.fnmatch(current_file, pattern)
                            for pattern in self.exclude
                        ):
                            continue
                        else:
                            self.diff += sc.runcommand(
                                f"git diff {'--patience ' if self.patience else ''}{self.v_from} {self.v_to} -- {current_file}"
                            )
            else:
                with aim.utils.TemporaryDirectoryChange(self.library):
                    assert not sc.runcommand(
                        f"git rev-parse --verify {self.v_from}"
                    ).startswith("fatal"), "Invalid v_from"
                    assert not sc.runcommand(
                        f"git rev-parse --verify {self.v_to}"
                    ).startswith("fatal"), "Invalid v_to"
                    self.diff = sc.runcommand(f"git diff {self.v_from} {self.v_to}")

    def parse_diff(self):
        self.log("Parsing the diff")
        self.git_diff = aim.GitDiff(
            self.diff, include_patterns=self.include, exclude_patterns=self.exclude
        )
        self.git_diff.summarize()  # summarize
        self.n_tokens = self.git_diff.count_all_tokens(
            model=self.model
        )  # NB: not implemented for all models
        if self.verbose and (self.n_tokens > -1):
            print(f"Number of tokens in the diff: {self.n_tokens}")

    def make_prompts(self):
        diff_string = self.git_diff.get_diff_string()
        for code_file in self.code_files:
            code_file.make_prompt(
                self.base_prompt,
                prompt_kwargs={
                    "library": self.library.stem,
                    "library_alias": f" ({self.library_alias})"
                    if self.library_alias
                    else "",
                    "diff": diff_string,
                },
                encoder=self.encoder,
            )
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
