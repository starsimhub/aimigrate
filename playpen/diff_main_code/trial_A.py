""" trial_A.py
"""
import os
import json
import tiktoken
import aimigrate as aim

# change cwd to the directory of this file
os.chdir(os.path.dirname(__file__))

def run_trial(model: str, report_token_count: bool = False):
    # file with the code
    code_file = aim.paths.data / 'zombiesim' / 'zombie.py' # v0.5.2

    # file with the diff
    diff_file = aim.paths.data / 'zombiesim' / 'zombiesim.diff'

    # class for parsing the diff
    include_patterns = ["*.py", "starsim/diseases/sir.py"]; exclude_patterns = ["docs/*", "starsim/__init__.py", "starsim/diseases/*", "setup.py", "tests/*"] # Number of tokens 113743
    git_diff = aim.GitDiff(diff_file, include_patterns=include_patterns, exclude_patterns=exclude_patterns)
    git_diff.summarize() # summarize
    if report_token_count:
        print(f'Number of tokens {git_diff.count_all_tokens(model=model)}')

    # class for parsin the code
    python_code = aim.PythonCode(code_file)

    # chatter
    chatter = aim.SimpleQuery(model=model)

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
    with open(f"results/{code_file.stem}_{model}_A.json", "w") as f:
        json.dump(response.to_json(), f, indent=2)


if __name__ == "__main__":
    for model in ['gpt-4o-mini', 'gpt-4o', 'gemini-1.5-flash', 'gemini-1.5-flash-8b']:
        print(f"Running trial for model {model}")
        try:
            run_trial(model)
        except Exception as e:
            print(f"Error running trial for model {model}: {e}")
    print("done")