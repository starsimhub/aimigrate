"""
Define embedding options for different LLMs.
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings


class EmbeddingModels(Enum):
    OPENAI = {
        "text-embedding-3-small",
        "text-embedding-3-large",
        "text-embedding-ada-002",
    }
    GEMINI = {"models/text-embedding-004", "models/embedding-001"}


# Pydantic model for configuration
class EmbeddingModelsConfig(BaseModel):
    model: str = Field(..., description="The name of the model to use")
    provider: str = None  # To be derived dynamically

    def __init__(self, **data):
        super().__init__(**data)
        self.provider = self.set_provider(self.model)

    @field_validator("model")
    @classmethod
    def validate_model(cls, model):
        for provider in EmbeddingModels:
            if model in provider.value:
                return model
        raise ValueError(f"Model '{model}' not found in any provider.")

    @field_validator("provider")
    @classmethod
    def set_provider(cls, model):
        for provider_enum in EmbeddingModels:
            if model in provider_enum.value:
                return provider_enum.name
        raise ValueError(f"No provider found for model '{model}'.")


class SimpleEmbedding:
    """
    A simple interface to get an embedding
    """

    def __init__(self, model="text-embedding-3-small"):
        # Validate and parse the configuration
        self.config = EmbeddingModelsConfig(model=model)

        # Setup the embeddings based on provider
        if self.config.provider == "OPENAI":
            self.embeddings = OpenAIEmbeddings(model=self.config.model)
        elif self.config.provider == "GEMINI":
            self.embeddings = GoogleGenerativeAIEmbeddings(model=self.config.model)
        else:
            raise ValueError(
                f"Unsupported provider. Choose {[e.name for e in EmbeddingModels]}"
            )

    def get_embedding(self, input_text: str):
        return self.embeddings.embed_query(input_text)

    def count_tokens(self, input_text: str):
        return len(input_text.split())
