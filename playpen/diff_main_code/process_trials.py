""" process_trials.py
Take the results from the trials and process them into python scripts
"""

import os
import re
import json
from pathlib import Path
import aimigrate as aim
import matplotlib.pyplot as plt

os.chdir(os.path.dirname(__file__))

# directory with results
result_dir = Path(__file__).parent / 'results'

# file with the code
code_file = aim.paths.data / 'zombiesim' / 'zombie.py' # v0.5.2

# trial id
trial_id = 'B' # or trial_id = 'A'
# script name that was migrated/refactored
stem = code_file.stem

# find the files with the results
result_pattern = f'{stem}_*_{trial_id}.json'
results = list(result_dir.glob(result_pattern))
print(f"Found {len(results)} results for {stem} and trial {trial_id}")

# Extract the models from the filenames
model_pattern = re.compile(rf'{stem}_(.*?)_{trial_id}\.json')
models = [model_pattern.search(result.name).group(1) for result in results if model_pattern.search(result.name)]

print(f"Extracted models: {models}")
for model in models:

    print(f"Processing {stem} and model {model} and trial {trial_id}")
    # load the model results
    with open(result_dir / f"{stem}_{model}_{trial_id}.json", 'r') as f:
        result = json.load(f)

    # grab the code string
    result_string = result['kwargs']['content']
    match_pattern = re.compile(r'```python(.*?)```', re.DOTALL)
    code_match = match_pattern.search(result_string)

    # write to the file
    with open(result_dir / f"{stem}_{model}_{trial_id}.py", 'w') as f:
        f.write(code_match.group(1))
    
print("done")
