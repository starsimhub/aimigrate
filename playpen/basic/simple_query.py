""" chat.py
How to use SimpleQuery to query the LLM.
"""
import starsim_ai as sa

chatter = sa.SimpleQuery(model='meta-llama/Llama-3.2-1B')
response = chatter("Hi, I'm in Oregon. What is the state to the North of me?")
print(response)
