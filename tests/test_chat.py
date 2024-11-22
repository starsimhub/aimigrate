import pytest
from starsim_ai.chat import SimpleQuery

# FILE: tests/test_chat.py


def test_simplequery_creation_openai():
    chat = SimpleQuery(model='gpt-3.5-turbo')
    assert chat.config.provider == 'OPENAI'

def test_simplequery_creation_gemini():
    chat = SimpleQuery(model='gemini-1.5-flash')
    assert chat.config.provider == 'GEMINI'

def test_simplequery_creation_invalid_model():
    with pytest.raises(ValueError, match=r"Model '.*' not found in any provider\."):
        SimpleQuery(model='invalid-model')
        # FILE: tests/test_chat.py

def test_simplequery_chat_openai():
    chatter = SimpleQuery(model='gpt-3.5-turbo')
    response = chatter("Is a tomato a fruit or a vegetable?")
    response.pretty_print()

def test_simplequery_chat_gemini():
    chatter = SimpleQuery(model='gemini-1.5-flash')
    response = chatter("Is a tomato a fruit or a vegetable?")
    response.pretty_print()
