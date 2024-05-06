WebRTC AI Voice Chat
====================

Overview
--------

The goal of this project is to demo `speech <-> langchain <-> audio` workflow.

1. Speech to text is using [OpenAI's open source Whisper mini](https://huggingface.co/openai/whisper-small) model.
2. Chat model used for this demo is [Microsoft's Phi3](https://azure.microsoft.com/en-us/blog/introducing-phi-3-redefining-whats-possible-with-slms/) model running locally using [Ollama](https://ollama.com/).
3. Text to Audio is using [Suno's open source Bark small](https://huggingface.co/suno/bark-small) model.

