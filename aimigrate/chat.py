import aisuite as ai

__all__ = ["SimpleQuery"]

class SimpleQuery():
    """
    A simple query interface to interact with an AI model.
    """

    def __init__(self, model="openai:gpt-3.5-turbo", **kwargs):
        self.model = model
        self.client = ai.Client()
        self.kwargs = {'temperature':0.7} | kwargs
        
    def __call__(self, user_input):
        return self.chat(user_input)
    
    def chat(self, user_input):
        messages = [
            {"role": "system", "content": "You are a helpful software engineer."},
            {"role": "user", "content": user_input},
        ]        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **self.kwargs
        )
        return response.choices[0].message.content