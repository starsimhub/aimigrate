""" chat.py
How to use SimpleQuery to query the LLM.
"""
import starsim_ai as sa

chatter = sa.SimpleQuery(model='gemini-1.5-flash')
response = chatter("Hi, I'm in Oregon. What is the state to the North of me?")
response.pretty_print()
