from langchain_core.prompts import PromptTemplate

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from enum import Enum
from pydantic import BaseModel, Field, field_validator

class ProviderModels(Enum):
    OPENAI = {'gpt-3.5-turbo', 'gpt-4o', 'gpt-4o-mini', 'o1-mini', 'o1-preview'}
    GEMINI = {'gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-1.5-pro'}

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
        for provider in ProviderModels:
            if model in provider.value:
                return model
        raise ValueError(f"Model '{model}' not found in any provider.")

    @field_validator("provider")
    @classmethod
    def set_provider(cls, model):
        for provider_enum in ProviderModels:
            if model in provider_enum.value:
                return provider_enum.name
        raise ValueError(f"No provider found for model '{model}'.")


class SimpleQuery():
    """
    A simple query interface to interact with an AI model.
    """
    def __init__(self, model='gpt-3.5-turbo'):
        # Validate and parse the configuration
        self.config = LLMConfig(model=model)

        # Setup the LLM based on provider
        if self.config.provider == 'OPENAI':
            self.llm = ChatOpenAI(model=self.config.model)
        elif self.config.provider == 'GEMINI':
            self.llm = ChatGoogleGenerativeAI(model=self.config.model)
        else:
            raise ValueError(f"Unsupported provider. Choose {[e.name for e in ProviderModels]}")

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