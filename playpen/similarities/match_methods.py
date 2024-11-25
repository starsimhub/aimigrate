""" match_methods.py
Match methods between two classes

References:
- https://python.langchain.com/docs/how_to/output_parser_json/
"""

import os
import json
import starsim_ai as sa

# my original prompt
prompt_string = '''
Here is one version of my code (code_A):
```python
{}
```
and here is the new version of my code (code_B):
```python
{}
```
Create a dictionary that matches the classes and their methods between the classes in the two versions of the code (code_A and code_B). Names of the classes and methods may have changed between the two versions.
Return the dictionary in the format where class_n is the name of the class and method_n is the name of the method:
{{ 'code_A.class_0.method_0': 'code_B.class_0:method_0', 'code_A.class_0.method_1': 'code_B.class_0:method_1', ... }}
'''

# o1-preview-new-prompt
new_prompt_string = '''
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
- Match each class and its methods from code_A to the corresponding class and methods in code_B, even if the names have changed.
- Create a dictionary that maps each class and method in code_A to its counterpart in code_B.

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


# change to current directory
os.chdir(os.path.dirname(__file__))

# set the file names
file_A = sa.paths.data / 'zombiesim' / 'zombie.py' # v0.5.2
file_B = sa.paths.data / 'zombiesim' / 'zombie_ref.py' # v2.1.1

# load the code as strings
code_A_str = sa.PythonCode(file_A).get_code_string()
code_B_str = sa.PythonCode(file_B).get_code_string()

prompt = new_prompt_string.format(code_A_str, code_B_str)

parser = {}
chatter = sa.JSONQuery(parser, model='gpt-4o')
response = chatter(prompt)

# save the response
with open("match_methods.json", "w") as f:
    json.dump(response, f, indent=2)


