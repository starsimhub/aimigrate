"""
Helper classes for parsing code in a rigorous way.
"""

import ast
import sciris as sc


class ClassVisitor(ast.NodeVisitor):
    """
    A visitor class that collects information about class definitions in an AST (Abstract Syntax Tree).

    **Example usage**::

        script = '''
        class MyClass:
            def method(self):
                pass
        '''
        tree = ast.parse(script)
        visitor = ClassVisitor()
        visitor.visit(tree)
        print(visitor.classes)
        # Output: [{'name': 'MyClass', 'bases': [], 'methods': ['method'], 'lineno': 2, 'end_lineno': 4}]
    """

    def __init__(self):
        self.classes = []

    def visit_ClassDef(self, node):
        if isinstance(node, ast.ClassDef):
            # Collect class details
            class_info = sc.objdict(
                {
                    "name": node.name,
                    "bases": [
                        base.id if isinstance(base, ast.Name) else ast.dump(base)
                        for base in node.bases
                    ],
                    "methods": [
                        n.name for n in node.body if isinstance(n, ast.FunctionDef)
                    ],
                    "lineno": node.lineno,
                    "end_lineno": getattr(node, "end_lineno", None),  # Python 3.8+
                }
            )
            self.classes.append(class_info)
        self.generic_visit(node)  # Continue visiting child nodes


class MethodVisitor(ast.NodeVisitor):
    """
    A visitor class that collects information about methods in a specific class
    within an Abstract Syntax Tree (AST).

    **Example usage**::
    
        script = '''
        class MyClass:
            def method1(self):
                pass

            def method2(self):
                return "Hello"
        '''
        tree = ast.parse(script)
        visitor = MethodVisitor('MyClass')
        visitor.visit(tree)
        print(visitor.methods)
        # Output:
        # [{'name': 'method1', 'lineno': 3, 'end_lineno': 4},
        #  {'name': 'method2', 'lineno': 6, 'end_lineno': 7}]
    """

    def __init__(self):
        self.methods = []

    def visit_ClassDef(self, node):
        # Visit each method (FunctionDef) in the class body
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                method_info = sc.objdict(
                    {
                        "name": child.name,
                        "lineno": child.lineno,
                        "end_lineno": getattr(child, "end_lineno", None),  # Python 3.8+
                    }
                )
                self.methods.append(method_info)
        # Continue visiting child nodes
        self.generic_visit(node)
