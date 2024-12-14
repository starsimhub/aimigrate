"""
Migrate Typhoidsim files from v1.0.3 to v2.2.0. 
"""
import os
import json
import tiktoken
import sciris as sc
import starsim_ai as sa

# change cwd to the directory of this file
os.chdir(sc.thisdir(__file__))

def migrate(code_file, model='gpt-4o', diff_file='starsim_v1.0.3-v2.2.0.diff', report_token_count=False):
    
    code_file = sc.path(code_file)

    # class for parsing the diff
    include_patterns = ["*.py", "starsim/diseases/sir.py"]; exclude_patterns = ["docs/*", "starsim/__init__.py", "starsim/diseases/*", "setup.py", "tests/*"] # Number of tokens 113743
    git_diff = sa.GitDiff(diff_file, include_patterns=include_patterns, exclude_patterns=exclude_patterns)
    git_diff.summarize() # summarize
    if report_token_count:
        print(f'Number of tokens {git_diff.count_all_tokens(model=model)}')

    # class for parsin the code
    python_code = sa.PythonCode(code_file)

    # chatter
    chatter = sa.SimpleQuery(model=model)

    # encoder (for counting tokens)
    encoder = tiktoken.encoding_for_model("gpt-4o")
        
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
    if report_token_count:
        print(f"Number of tokens {len(encoder.encode(prompt))}")

    # $$
    response = chatter(prompt)

    # write to file (process later)
    outfile = f"results/{code_file.stem}_migrated.json"
    sc.savejson(outfile, response.to_json())


if __name__ == "__main__":

    # Settings
    code_file = 'typhoidsim/environment.py'
    models = ['gpt-4o-mini', 'gpt-4o', 'gemini-1.5-flash', 'gemini-1.5-flash-8b']
    model = models[1]

    # Do the migration
    with sc.timer():
        migrate(code_file, model)
