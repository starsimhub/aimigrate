""" simple_json.py
Show how to use the JSONQuery class to create JSON formatted output
"""

from pydantic import BaseModel, Field
import starsim_ai as sa

# Example using Pydantic model
class Joke(BaseModel):
    setup: str = Field(description="question to set up a joke")
    punchline: str = Field(description="answer to resolve the joke")  

chatter = sa.JSONQuery(Joke, model='gpt-3.5-turbo')

response = chatter.chat("Tell me a joke")
print(response)

# Example using a dictionary
parser = {"code": "python code"}
chatter = sa.JSONQuery(parser, model='gpt-3.5-turbo')
response = chatter("Code the fibonnaci sequence in python?")
print(response)
