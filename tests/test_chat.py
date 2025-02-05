import aimigrate as aim

def test_SimpleQuery():
    chatter = aim.SimpleQuery(model='openai:gpt-4o-mini')
    response = chatter("Hi, I'm in Oregon. What is the state to the North of me?")
    assert isinstance(response, str)
