# Starsim AI

Starsim AI (ssAI) has two parts: ssAI-Migrate helps migrate code between different versions of Starsim, while ssAI-Copilot (coming soon!) is a VSCode-integrated bespoke coding assistant.

**Warning**: Setting up Starsim AI to run locally requires knowledge of machine learning libraries, API keys, etc. It is not like typing a question into ChatGPT. Please contact info@starsim.org for more information.


## Setup


### 1. Install dependencies

Dependencies can be installed via:
```python
pip install -e .
```

Or use `uv` or your environment manager of choice.

*Note:* This project requires PyTorch, CUDA libraries, etc. For a typical system, ~2 GB of libraries will be downloaded.


### 2. Configure OpenAI and/or Gemini

To use these tools you will need an API key. Google/Gemini provides them for free, but you have to pay for one for OpenAI.

For Gemini, get your API key from: https://aistudio.google.com/apikey

For OpenAI, get your API key from: https://platform.openai.com/settings/organization/api-keys

Once you have these keys, store them as environment variables `GEMINI_API_KEY` and `OPENAI_API_KEY`, respectively. If you use Linux or Mac, a good way to do this is to save them as a file on your computer, and then load them with e.g.:
```bash
export GEMINI_API_KEY=$(cat ~/gemini_api_key)
```

**DO NOT UNDER ANY CIRCUMSTANCE SHARE OR UPLOAD YOUR API KEY!!!!!!!!!!!!!!!!**

## Usage

Let's say we have a project *Zombiesim* that we want to migrate from Starsim v1 (v1.0.3) to v2 (v2.2.0). Typical usage is to migrate all the files in a folder to a new folder:
```py
import starsim as ss
import aimigrate as aim

aim.migrate(
    starsim = ss, # can also be the path to the starsim folder, which must be the cloned repo (not from pypi)
    from_version = 'v1.0.3', # can be any valid git tag or hash
    to_version = 'v2.2.0',
    model = 'gpt-4o', # see ssai.model_options for list of allowed models
    source = '/path/to/your/code/folder', # folder with the code to migrate
    dest = '/path/to/migrated/folder', # folder to output migrated code into
)
```

**Running local models**:
We use `ollama` to run models locally. To start open a terminal run `ollama serve`. If it is your first time running the model you'll need to pull it first (e.g., `ollama run llama3`).
