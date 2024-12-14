"""
Migrate Typhoidsim files from v1.0.3 to v2.2.0. 
"""
import os
import re
import tiktoken
import sciris as sc
import starsim_ai as sa

# change cwd to the directory of this file
os.chdir(sc.thisdir(__file__))

def migrate(code_file, model='gpt-4o', diff_file='starsim_v1.0.3-v2.2.0.diff', out_dir='migrated', report_token_count=False):
    
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
