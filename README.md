# AIMigrate

AIMigrate helps migrate code to maintain compatability when one of your dependency packackages changes


## Installation
```
pip install aimigrate
```

### Configure LLM Provider

AIMigrate is compatabile with openai, gemini, and anthropic models. To use these tools you will need an API key. 

- For Gemini, get your API key from: https://aistudio.google.com/apikey
- For OpenAI, get your API key from: https://platform.openai.com/settings/organization/api-keys
- For Anthropic, get your API key from: https://www.anthropic.com/api

Once you have these keys, we recommend using [python-dotenv](https://pypi.org/project/python-dotenv/) for managing your keys. Store them as environment variables `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` respectively.

**Running open weight (i.e., local) models**:
You can also use `ollama` to run models locally. To start open a terminal run `ollama serve`. If it is your first time running the model you'll need to pull it first (e.g., `ollama run llama3`). You will likely need to [increase the context window](https://github.com/ollama/ollama/blob/main/docs/faq.md#:~:text=How%20can%20I%20specify%20the%20context%20window%20size%3F).

**DO NOT UNDER ANY CIRCUMSTANCE SHARE OR UPLOAD TO GITHUB YOUR API KEY!**

## Usage

Let's say we have a project *Zombiesim* that we want to migrate from Starsim v1 (v1.0.3) to v2 (v2.2.0). Typical usage is to migrate all the files in a folder to a new folder:
```py
import starsim as ss
import aimigrate as aim

aim.migrate(
    starsim = ss, # can also be the path to the folder, which must be the cloned repo (not from pypi)
    from_version = 'v1.0.3', # can be any valid git tag or hash
    to_version = 'v2.2.0', # can be any valid git tag or hash
    model = 'openai:gpt-4o', # use aisuite provider:model syntax
    source = '/path/to/your/code/folder', # folder with the code to migrate
    dest = '/path/to/migrated/folder', # folder to output migrated code into
)
```

## Tests
```
uv run --group dev pytest -v test_*.py
```