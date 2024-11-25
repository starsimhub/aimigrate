""" calculate_similarities.py
"""
import os
import json
import sciris as sc
import pandas as pd
from scipy.spatial import distance
from scipy.stats import pearsonr
from langchain_openai import OpenAIEmbeddings
import starsim_ai as sa

# change cwd to the directory of this file
os.chdir(os.path.dirname(__file__))

# function for calculating similarity between strings
def calculate_similarity(v1,v2):
    res = sc.objdict()
    res['cosine'] = distance.cosine(v1, v2)
    res['euclidean'] = distance.euclidean(v1, v2)
    res['pearsonr'] = pearsonr(v1, v2)[0]
    return res


def calculate_code_similarity(code_A, code_B):
    """
    Calculate similarity between two codes
    """

    # load the match dict
    with open("match_methods.json", "r") as f:
        match_methods = json.load(f)
    match_classes = {k.split('.')[0]:v.split('.')[0] for k,v in match_methods.items()}

    # parse the code
    classes_A = sa.PythonCode(code_A)
    classes_B = sa.PythonCode(code_B)

    # create embedder
    embedder = sa.SimpleEmbedding(model='text-embedding-3-small')

    # calculate similarity by matching classes
    class_results = sc.objdict()
    for class_name in match_classes:
    # for class_name in [c['name'] for c in classes_A.classes]:
        print("Class:", class_name)

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
                
    with open(f'class_results_{code_B.stem}.json', 'w') as f:
        json.dump(class_results, f, indent=2)

    # calculate similarity by matching class methods
    method_results = sc.objdict()
    for method_name in match_methods.keys():
        print("Method:", method_name, ':', match_methods[method_name])

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
        
    with open(f'methods_result_{code_B.stem}.json', 'w') as f:
        json.dump(method_results, f, indent=2)


def plot_code_similarity(stem):
    """
    Plot the similarity results
    """
    
    import matplotlib.pyplot as plt

    with open(f'class_results_{stem}.json', 'r') as f:
        class_results = pd.DataFrame(json.load(f))

    with open(f'methods_result_{stem}.json', 'r') as f:
        method_results = pd.DataFrame(json.load(f))

    metrics = list(calculate_similarity([0, 1], [1, 0]).keys())
    num_metrics = len(calculate_similarity([0, 1], [1, 0]))

    fig, axes = plt.subplots(1, 3, figsize=(4*num_metrics, 6))
    for i, k in enumerate(metrics):
        kwargs = {}

        ax = axes[i]
        if i == 0:
            kwargs['label'] = "Class"        
        ax.plot(class_results['class'], class_results[k], 'o', **kwargs)

        if i == 0:
            kwargs['label'] = "Method"        
        ax.plot(method_results['class'], method_results[k], 'x', **kwargs)

        ax.set_title(f'{k}')

        # rotate x-axis labels by 90 degrees
        ax.set_xticklabels(class_results['class'], rotation=90)

        if i == 0:
            ax.legend(frameon=False)

    plt.tight_layout()
    plt.savefig(f'similarity_{stem}.png')
    print("done")

if __name__ == '__main__':
    # files for code comparison
    code_A = sa.paths.data / 'zombiesim' / 'zombie.py' # v0.5.2
    code_B = sa.paths.data / 'zombiesim' / 'zombie_ref.py' # v2.1.1

    # calculate similarity metrics between the two codes
    calculate_code_similarity(code_A, code_B)

    # plot results
    plot_code_similarity(code_B.stem)

    print("done")