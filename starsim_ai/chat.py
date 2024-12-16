from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.llms import VLLM

from enum import Enum
from typing import Dict, Union, Type
from pydantic import BaseModel, Field, field_validator

class LLMModels(Enum):
    OPENAI = {'gpt-3.5-turbo', 'gpt-4o', 'gpt-4o-mini', 'o1-mini', 'o1-preview'}
    GEMINI = {'gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-1.5-pro'}
    HUGGINGFACE = {'meta-llama/Llama-2-7b-chat-hf', 'meta-llama/Llama-3.2-1B'}


class BaseQuery():
    def __init__(self, model='gpt-3.5-turbo', **kwargs):
        # Validate and parse the configuration
        self.config = LLMConfig(model=model)

        # Setup the LLM based on provider
        if self.config.provider == 'OPENAI':
            self.llm = ChatOpenAI(model=self.config.model, **kwargs)
        elif self.config.provider == 'GEMINI':
            self.llm = ChatGoogleGenerativeAI(model=self.config.model, **kwargs)
        elif self.config.provider == 'HUGGINGFACE':
            self.llm = VLLM(
                model=self.config.model, **kwargs
            )
        else:
            raise ValueError(f"Unsupported provider. Choose {[e.name for e in LLMModels]}")    


# Pydantic model for configuration
class LLMConfig(BaseModel):
    model: str = Field(..., description="The name of the model to use")
    provider: str = None  # To be derived dynamically

    def __init__(self, **data):
        super().__init__(**data)
        self.provider = self.set_provider(self.model)

    @field_validator("model")
    @classmethod
    def validate_model(cls, model):
        for provider in LLMModels:
            if model in provider.value:
                return model
        raise ValueError(f"Model '{model}' not found in any provider.")

    @field_validator("provider")
    @classmethod
    def set_provider(cls, model):
        for provider_enum in LLMModels:
            if model in provider_enum.value:
                return provider_enum.name
        raise ValueError(f"No provider found for model '{model}'.")
        
        
class SimpleQuery(BaseQuery):
    """
    A simple query interface to interact with an AI model.
    """
    def __init__(self, model='gpt-3.5-turbo'):
        super().__init__(model)

        # Setup the prompt and chain
        self.prompt = PromptTemplate(
            input_variables=["user_input"],
            template="{user_input}",
        )
        self.chain = self.prompt | self.llm

    def __call__(self, user_input):
        return self.chat(user_input)

    def chat(self, user_input):
        response = self.chain.invoke(user_input)
        return response
    
class JSONQuery(BaseQuery):
    """
    A query interface that returns the response in JSON format.

    Example: 

        # Define your desired data structure.
        class Joke(BaseModel):
            setup: str = Field(description="question to set up a joke")
            punchline: str = Field(description="answer to resolve the joke")
        chatter = JSONQuery(parser=Joke, model='gpt-3.5-turbo')

        # Or define your desired data structure using a dictionary.
        parser = {"setup": "question to set up a joke", "punchline": "answer to resolve the joke"}
        chatter = JSONQuery(parser=parser, model='gpt-3.5-turbo')

    Reference:
    https://python.langchain.com/docs/how_to/output_parser_json/
    """
    def __init__(self, parser: Union[Type[BaseModel], dict], model: str='gpt-3.5-turbo'):
        """
        Initializes the JSONQuery instance.

        Args:
            parser (BaseModel, Dict): The structure of the expected JSON response.
            model (str): The name of the model to use. Defaults to 'gpt-3.5-turbo'.
        """        
        super().__init__(model)

        # Set up a parser + inject instructions into the prompt template.
        if isinstance(parser, dict):
            parser = self.create_pydantic_model('Query', parser)
        self.parser = JsonOutputParser(pydantic_object=parser)

        # Setup the prompt and chain
        self.prompt = PromptTemplate(
            template="Answer the user query.\n{format_instructions}\n{query}\n",
            input_variables=["query"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
        self.chain = self.prompt | self.llm | self.parser

    def __call__(self, user_input):
        return self.chat(user_input)

    def chat(self, user_input):
        response = self.chain.invoke({"query": user_input})
        return response
        
    @staticmethod
    def create_pydantic_model(class_name: str, fields: Dict[str, str]) -> Type[BaseModel]:
        """
        Dynamically create a Pydantic model class.
        
        Args:
            class_name (str): The name of the class to create.
            fields (Dict[str, str]): A dictionary where keys are field names 
                                    and values are field descriptions.
        
        Returns:
            Type[BaseModel]: The dynamically created Pydantic model class.
        """
        # Prepare the annotations dictionary
        annotations = {key: (str, Field(description=value)) for key, value in fields.items()}
        
        # Create the Pydantic model dynamically
        return type(class_name, (BaseModel,), {"__annotations__": {k: v[0] for k, v in annotations.items()}, **{k: v[1] for k, v in annotations.items()}})
