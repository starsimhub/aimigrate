"""
Define the different `Query` classes, which include the `chat()` interface.
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator
import sciris as sc

from langchain_core.prompts import PromptTemplate

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from langchain_community.llms import VLLM

from langchain_community.callbacks import get_openai_callback

import aimigrate as ai

__all__ = ["Models", "BaseQuery", "SimpleQuery"]

MODELS = sc.odict(
    {
        "gpt-3.5-turbo": "gpt-3.5-turbo-0125",
        "gpt-4o": "gpt-4o-2024-08-06",
        "gpt-4o-mini": "gpt-4o-mini-2024-07-18",
        "o1-mini": "o1-mini-2024-09-12",
        "o1-preview": "o1-preview-2024-09-12",
        "o1": "o1-2024-12-17",
        "llama3-8b": "llama3",
        "llama3-70b": "llama3:70b",
        "llama3-8b-128k": "llama3:8b_128k",
        "codellama-70b": "codellama:70b",
        "gemini-2.0-flash-exp": "gemini-2.0-flash-exp",
        "claude-3.5-haiku": "claude-3-5-haiku-20241022",
        "claude-3.5-sonnet": "claude-3-5-sonnet-20241022",
    }
)


class Models(Enum):
    OPENAI = {
        "gpt-3.5-turbo-0125",
        "gpt-4o-2024-08-06",
        "gpt-4o-mini-2024-07-18",
        "o1-mini-2024-09-12",
        "o1-preview-2024-09-12",
        "o1-2024-12-17",
    }
    GEMINI = {"gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-2.0-flash-exp"}
    OLLAMA = {"llama3:70b", "llama3", "codellama:70b", "llama3:8b_128k"}
    ANTHROPIC = {"claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"}


class BaseQuery(sc.prettyobj):
    """
    Define an LLM query

    Key args:
        model="gpt-4o",
        temperature=0.7,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    """

    def __init__(self, model="gpt-3.5-turbo", temperature=0.7, **kwargs):
        # Update sampling temperature
        kwargs.update({"temperature": temperature})

        # Validate and parse the configuration
        self.config = LLMConfig(model=MODELS[model])
        self.get_callback = ai.utils.EmptyCallback
        self.cost = {"total": 0, "prompt": 0, "completion": 0, "cost": 0}

        # Setup the LLM based on provider
        if self.config.provider == "OPENAI":
            self.llm = ChatOpenAI(model=self.config.model, **kwargs)
            self.get_callback = get_openai_callback
        elif self.config.provider == "GEMINI":
            self.llm = ChatGoogleGenerativeAI(model=self.config.model, **kwargs)
        elif self.config.provider == "ANTHROPIC":
            self.llm = ChatAnthropic(model=self.config.model, **kwargs)
        elif self.config.provider == "OLLAMA":
            self.llm = ChatOllama(model=self.config.model, **kwargs)
        elif self.config.provider == "HUGGINGFACE":
            self.llm = VLLM(model=self.config.model, **kwargs)
        else:
            raise ValueError(f"Unsupported provider. Choose {[e.name for e in Models]}")

    def __call__(self, user_input):
        return self.llm.invoke(user_input)

    def update_cost(self, cb):
        self.cost["total"] += cb.total_tokens
        self.cost["prompt"] += cb.prompt_tokens
        self.cost["completion"] += cb.completion_tokens
        self.cost["cost"] += cb.total_cost


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
        for provider in Models:
            if model in provider.value:
                return model
        raise ValueError(f"Model '{model}' not found in any provider.")

    @field_validator("provider")
    @classmethod
    def set_provider(cls, model):
        for provider_enum in Models:
            if model in provider_enum.value:
                return provider_enum.name
        raise ValueError(f"No provider found for model '{model}'.")


class SimpleQuery(BaseQuery):
    """
    A simple query interface to interact with an AI model.
    """

    def __init__(self, model="gpt-3.5-turbo", **kwargs):
        super().__init__(model, **kwargs)

        # Setup the prompt and chain
        self.prompt = PromptTemplate(
            input_variables=["user_input"],
            template="{user_input}",
        )
        self.chain = self.prompt | self.llm

    def __call__(self, user_input):
        return self.chat(user_input)

    def chat(self, user_input):
        with self.get_callback() as cb:
            response = self.chain.invoke(user_input)
        if not isinstance(cb, ai.utils.EmptyCallback):
            self.update_cost(cb)
        return response