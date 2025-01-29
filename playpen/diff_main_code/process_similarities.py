""" process_similarities.py
"""

import re
import os
import json
import sciris as sc
import pandas as pd
import numpy as np
import aimigrate as aim
import matplotlib.pyplot as plt

from pathlib import Path
from scipy.spatial import distance
from scipy.stats import pearsonr

# change cwd to the directory of this file
os.chdir(os.path.dirname(__file__))


def calculate_similarity(v1,v2):
    # function for calculating similarity between strings

    res = sc.objdict()
    res['cosine'] = distance.cosine(v1, v2)
    res['euclidean'] = distance.euclidean(v1, v2)
    res['pearsonr'] = pearsonr(v1, v2)[0]
    return res


def match_methods(file_A, file_B, model='gpt-4o-mini', result_dir=None):
    # prompt string for matching methods (see playpen/similarities/match_methods.py)
    prompt_string = '''
    Task:

    You have two versions of your Python code: code_A and code_B. The code snippets are as follows:

    Version A (code_A):

    ```python
    {}
    ```

    Version B (code_B):

    ```python
    {}
    ```

    Instructions:

    - Analyze both versions of the code to identify all classes and their methods.
    - Match each class and its methods from code_A to the corresponding class and methods in code_B. code_A class or method names are fixed, but code_B names may have changed or be missing.
    - Create a dictionary that maps each class and method in code_A to its closest counterpart in code_B. 

    Return the dictionary matching code_A:code_B in the following format, where <class_name> is the name of the class and <method_name> is the name of the method:

    {{
        '<class_name>.<method_name>': '<class_name>.<method_name>',
        ...
    }}

    Example:

    {{
        'ClassOne.method_a': 'ClassAlpha.method_x',
        'ClassTwo.method_b': 'ClassBeta.method_y',
        ...
    }}
    Where 'ClassOne.method_a' in code_A corresponds to 'ClassAlpha.method_x' in code_B, and so on.

    Notes:

    Accuracy is crucial: Ensure that the mapping correctly reflects the functional correspondence between classes and methods, not just similar names.
    Consider code structure and functionality, especially if names have changed.
    The dictionary keys and values should be strings formatted exactly as specified.
    '''

    # load the code as strings
    with open(file_A, 'r') as f:
        code_A_str = f.read()
    with open(file_B, 'r') as f:
        code_B_str = f.read()

    prompt = prompt_string.format(code_A_str, code_B_str)

    parser = {}
    chatter = aim.JSONQuery(parser, model=model)
    response = chatter(prompt)

    # save the response
    with open(result_dir / f"match_methods_{file_B.stem}.json", "w") as f:
        json.dump(response, f, indent=2)


def run_match_methods(result_dir):

    # from the result directory, find all files that end with *.py
    code_files = list(result_dir.glob('*.py'))
    print(f"Found {len(code_files)} code files")

    for file in code_files:

        # set the file names
        file_A = aim.paths.data / 'zombiesim' / 'zombie_ref.py' # v2.1.1
        file_B = file

        print("Processing", file_B.stem)
        match_methods(file_A, file_B, result_dir=result_dir)


def calculate_similarities(file_A, result_dir=None):
    
    # find the match files
    match_files = list(result_dir.glob('match_methods_*.json'))
    print(f"Found {len(match_files)} match files")

    # create embedder
    embedder = aim.SimpleEmbedding(model='text-embedding-3-small')

    for file in match_files:
        print("Processing", file)

        # file has format match_methods_<stem>_<model>.json, use regex to extract the stem and model
        match = re.match(r'match_methods_(.+)\.json', file.name)
        if match:
            stem, = match.groups()
        else:
            print(f"Could not figure out filename from {file}")
            continue

        # load the match dict and identify classes to match
        with open(file, 'r') as f:
            match_methods = json.load(f)
        match_classes = {k.split('.')[0]:v.split('.')[0] for k,v in match_methods.items()}

        # parse the code
        try:
            classes_A = aim.PythonCode(file_A) # reference code
            classes_B = aim.PythonCode(result_dir / f"{stem}.py") # comparison code

            # calculate similarity by matching classes
            class_results = sc.objdict()
            for class_name in match_classes:
                print("Class:", class_name)

                try:
                    # strings
                    s_A = classes_A.get_class_string(class_name)
                    s_B = classes_B.get_class_string(match_classes[class_name].split('.')[0])

                    # vectors
                    v_A = embedder.get_embedding(s_A)
                    v_B = embedder.get_embedding(s_B)

                    # calculate similarity
                    similarity = calculate_similarity(v_A, v_B)

                    # save results
                    class_results.setdefault('class', []).append(class_name)
                    for k,v in similarity.items():
                        class_results.setdefault(k, []).append(v)

                except Exception as e:
                    print(f"Error calculating similarity (class): {e}")
                        
            with open(result_dir / f'class_similarities_{stem}.json', 'w') as f:
                json.dump(class_results, f, indent=2)


            # calculate similarity by matching class methods
            method_results = sc.objdict()
            for method_name in match_methods.keys():
                print("Method:", method_name, ':', match_methods[method_name])

                try:
                    # strings
                    s_A = classes_A.get_class_string(method_name.split('.')[0], methods_flag=True)
                    s_B = classes_B.get_class_string(match_methods[method_name].split('.')[0], methods_flag=True)

                    # vectors
                    v_A = embedder.get_embedding(s_A[method_name.split('.')[1]])
                    v_B = embedder.get_embedding(s_B[match_methods[method_name].split('.')[1]])

                    similarity = calculate_similarity(v_A, v_B)

                    method_results.setdefault('class', []).append(method_name.split('.')[0])
                    method_results.setdefault('method', []).append(method_name.split('.')[1])
                    for k,v in similarity.items():
                        method_results.setdefault(k, []).append(v)
                except Exception as e:
                    print(f"Error calculating similarity (method): {e}")
                    
            with open(result_dir / f'method_similarities_{stem}.json', 'w') as f:
                json.dump(method_results, f, indent=2)

        except Exception as e:
            print(f"Error parsing code: {e} (trial), \nmoving on...")
            continue


def plot_class_results(result_dir, reference_result_dir=Path(__file__).parents[1] / 'similarities'):
    # find the similarity files
    result_files = list(result_dir.glob('class_similarities_*.json'))

    # load reference results
    with open(reference_result_dir / "class_results_zombie_ref.json", "r") as f:
        results = pd.DataFrame(json.load(f)).set_index('class')

    for result_file in result_files:
        print("Processing", result_file)

        # create master dataframe
        try:
            # get stem
            match = re.match(r'class_similarities_(.+)\.json', result_file.name)
            stem,  = match.groups()

            # load the results
            with open(result_file, 'r') as f:
                these_results = pd.DataFrame(json.load(f)).set_index('class')
            new_names = {k: k + f'_{stem}' for k in these_results.columns}
            these_results.rename(columns=new_names, inplace=True)

            # merge with reference results
            results = pd.merge(results, these_results, left_index=True, right_index=True)
            
        except Exception as e:
            print(f"Error with results: {e}")
            continue        

    metrics = list(calculate_similarity([0, 1], [1, 0]).keys())
    fig, axes = plt.subplots(1, len(metrics), figsize=(len(metrics)*3, 4.5))
    for ix, metric in enumerate(metrics):
        ax = axes[ix]
        group = results[[c for c in results.columns if metric in c]]
        columns = group.columns
        for i, c in enumerate(columns):
            ax.plot(len(group)*[i], group[c], 'o')
            print(f"{c}: {group[c].median():e}")
        names = ['_'.join(c.split('_')[1:]) for c in columns]
        names[0] = "baseline"
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=90)
        ax.set_title(f'{metric}')

    plt.tight_layout()
    plt.savefig('similarity_class_results.png') 
    


def plot_methods_results(result_dir, reference_result_dir=Path(__file__).parents[1] / 'similarities'):
    # find the similarity files
    result_files = list(result_dir.glob('method_similarities_*.json'))

    # load reference results
    with open(reference_result_dir / "methods_result_zombie_ref.json", "r") as f:
        results = pd.DataFrame(json.load(f)).set_index(['class', 'method'])

    for result_file in result_files:
        print("Processing", result_file)

        # create master dataframe
        try:
            # get stem
            match = re.match(r'method_similarities_(.+)\.json', result_file.name)
            stem,  = match.groups()

            # load the results
            with open(result_file, 'r') as f:
                these_results = pd.DataFrame(json.load(f)).set_index(['class', 'method'])
            new_names = {k: k + f'_{stem}' for k in these_results.columns}
            these_results.rename(columns=new_names, inplace=True)

            # merge with reference results
            results = pd.merge(results, these_results, left_index=True, right_index=True)
            
        except Exception as e:
            print(f"Error with results: {e}")
            continue        

    metrics = list(calculate_similarity([0, 1], [1, 0]).keys())
    fig, axes = plt.subplots(1, len(metrics), figsize=(len(metrics)*3, 4.5))
    for ix, metric in enumerate(metrics):
        ax = axes[ix]
        group = results[[c for c in results.columns if metric in c]]
        columns = group.columns
        for i, c in enumerate(columns):
            ax.plot(len(group)*[i], group[c], 'o')
            print(f"{c}: {group[c].median():e}")
        names = ['_'.join(c.split('_')[1:]) for c in columns]
        names[0] = "baseline"
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=90)
        ax.set_title(f'{metric}')

    plt.tight_layout()
    plt.savefig('similarity_methods_results.png') 
    

if __name__ == '__main__':

    # directory with results
    result_dir = Path(__file__).parent / 'results'    

    # match the methods (LLM code -> refactored code)
    run_match_methods(result_dir)

    # calculate similarities
    calculate_similarities(aim.paths.data / 'zombiesim' / 'zombie_ref.py', result_dir=result_dir)

    # plot results
    plot_class_results(result_dir)
    plot_methods_results(result_dir)