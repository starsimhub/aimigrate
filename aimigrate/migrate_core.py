import re
import types
import tiktoken
import sciris as sc
import aimigrate as aim

__all__ = []
__all__ = ["CoreMigrate", "CoreCodeFile"]

# TODO: figure out how to expand the context to not need to exclude files
default_include = ["*.py"]
default_exclude = ["__init__.py", "setup.py"]


class CoreMigrate(sc.prettyobj):
    def make_code_files(self):
        if self.verbose:
            self.log("Parsing the files...")
        if self.files is None:
            self.files = aim.get_python_files(self.source_dir)
        else:
            self.files = sc.tolist(self.files)

        if not len(self.files):
            errormsg = (
                f"Could not find any Python files to migrate in {self.source_dir}"
            )
            raise FileNotFoundError(errormsg)

        for file in self.files:
            source = self.source_dir / file
            dest = self.dest_dir / file
            code_file = aim.CoreCodeFile(
                source=source, dest=dest, file=file
            )  # Actually do the processing
            self.code_files.append(code_file)

    def log(self, string, color="green"):
        """Print if self.verbose is True"""
        if self.verbose:
            printfunc = dict(
                default=print,
                red=sc.printred,
                green=sc.printgreen,
                blue=sc.printcyan,
                yellow=sc.printyellow,
            )[color]
            printfunc(string)
        return

    def run_single(self, code_file):
        """Where everything happens!!"""
        self.log(f"Migrating {code_file.file}")
        try:
            code_file.run(self.chatter, save=self.save)
        except Exception as E:
            errormsg = f"Could not parse {code_file.file}: {E}"
            self.errors.append(errormsg)
            raise E if self.die else print(errormsg)
        return

    def run(self):
        raise NotImplementedError

    def _run(self):
        """Run all steps of the process"""

        if self.encoder is None:
            self.make_encoder()
        if self.chatter is None:
            self.make_chatter()

        self.log(f"\nStarting migration of {self.source_dir}", color="blue")
        if self.verbose:
            self.log(f"\nMigrating {len(self.files)} files", color="blue")
            self.log(f"{sc.newlinejoin(self.files)}", color="default")
        assert len(self.code_files) == len(self.files), (
            f"Length of code_files ({len(self.code_files)}) does not match length of files ({len(self.files)})"
        )
        self.timer = sc.timer()
        if self.parallel:
            sc.parallelize(self.run_single, self.code_files, parallelizer="thread")
        else:
            for code_file in self.code_files:
                self.run_single(code_file)
        self.timer.toc("Total time")
        return

    def make_encoder(self):
        self.log("Creating encoder...")
        try:
            self.encoder = tiktoken.encoding_for_model(
                self.model
            )  # encoder (for counting tokens)
        except KeyError as E:
            self.log(f"Could not create encoder for {self.model}: {E}", color="yellow")
            self.encoder = None

    def make_chatter(self):
        """Create the LLM agent"""
        self.log("Creating agent...")
        self.chatter = aim.SimpleQuery(model=self.model, **self.model_kw)
        return

    def parse_library(self):
        """Extract the right folder for library"""
        self.log("Parsing library folder")
        if isinstance(self.library, types.ModuleType):
            self.library = sc.thispath(self.library).parent
        self.library = sc.path(self.library)
        if not self.library.is_dir():
            errormsg = f"The library must be supplied as the module or the folder path, not {self.library}"
            raise FileNotFoundError(errormsg)
        return


class CoreCodeFile(sc.prettyobj):
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
        self.cost = {"total": 0, "prompt": 0, "completion": 0, "cost": 0}
        if process:
            self.process_code()
        return

    def process_code(self):
        """Parse the Python file into a string"""
        self.python_code = aim.PythonCode(self.source)
        self.orig_str = self.python_code.get_code_string()
        return

    def make_prompt(self, base_prompt, prompt_kwargs, encoder=None):
        """Create the prompt for the LLM"""
        self.prompt = base_prompt.format(code=self.orig_str, **prompt_kwargs)
        if encoder is not None:
            self.n_tokens = len(
                encoder.encode(self.prompt)
            )  # Not strictly needed, but useful to know
        else:
            self.n_tokens = -1
        return

    def run_query(self, chatter):
        """Where everything happens!!"""
        with sc.timer(self.file) as self.timer:
            self.response = chatter(self.prompt)
        return self.response

    def parse_response(self):
        """Extract code from the response object"""
        json = self.response.to_json()
        result_string = json["kwargs"]["content"]
        match_patterns = [r"```python(.*?)```", r"```(.*?)```"]
        for match_pattern in match_patterns:
            code_match = re.compile(match_pattern, re.DOTALL).search(result_string)
            if code_match:
                break
        if code_match:
            self.new_str = code_match.group(1)
        else:
            self.new_str = result_string
        return

    def run(self, chatter, save=True):
        """Run the migration, using the supplied LLM (chatter)"""
        self.run_query(chatter)
        self.parse_response()
        if save:
            self.save()
        return self.response

    def save(self):
        """Write to file"""
        sc.makefilepath(self.dest, makedirs=True)
        sc.savetext(self.dest, self.new_str)
        return
