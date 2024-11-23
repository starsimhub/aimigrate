""" trial_A.py
"""
import os
import json
import tiktoken
import starsim_ai as sa

# change cwd to the directory of this file
os.chdir(os.path.dirname(__file__))

# file with the code
code_file = sa.paths.data / 'zombiesim' / 'zombie.py' # v0.5.2

# file with the diff
diff_file = sa.paths.data / 'zombiesim' / 'zombiesim.diff'

# class for parsing the diff
include_patterns = ["*.py", "starsim/diseases/sir.py"]; exclude_patterns = ["docs/*", "starsim/__init__.py", "starsim/diseases/*", "setup.py", "tests/*"] # Number of tokens 113743
git_diff = sa.GitDiff(diff_file, include_patterns=["*.py"], exclude_patterns=exclude_patterns)
git_diff.summarize() # summarize
print(f'Number of tokens {git_diff.count_all_tokens(model="gpt-4o")}')

# class for parsin the code
python_code = sa.PythonCode(code_file)

# chatter
chatter = sa.SimpleQuery(model='gpt-4o')

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
print(f"Number of tokens {len(encoder.encode(prompt))}")

# $$
response = chatter(prompt)

# write to file (process later)
with open(f"{code_file.stem}.json", "w") as f:
    json.dump(response.to_json(), f, indent=2)

print("done")