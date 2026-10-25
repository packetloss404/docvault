from unittest.mock import MagicMock

from ai.providers.ollama_client import OllamaClient


def test_ollama_requests_have_timeout_token_and_cpu_bounds(settings, monkeypatch):
    settings.OLLAMA_REQUEST_TIMEOUT = 12.5
    settings.OLLAMA_MAX_TOKENS = 128
    settings.OLLAMA_NUM_THREADS = 2
    settings.OLLAMA_CONTEXT_WINDOW = 2048
    constructor = MagicMock()
    monkeypatch.setattr('ai.providers.ollama_client.ollama.Client', constructor)
    client = OllamaClient()
    constructor.assert_called_once_with(host=settings.LLM_API_ENDPOINT, timeout=12.5)
    client.generate('Question', max_tokens=32)
    assert constructor.return_value.chat.call_args.kwargs['options'] == {
        'temperature': 0.3, 'num_predict': 32, 'num_thread': 2, 'num_ctx': 2048,
    }
    client.embed('embedding text')
    assert constructor.return_value.embed.call_args.kwargs['options'] == {'num_thread': 2, 'num_ctx': 2048}
    client.embed_batch(['one', 'two'])
    assert constructor.return_value.embed.call_args.kwargs['options'] == {'num_thread': 2, 'num_ctx': 2048}


def test_nonpositive_ollama_options_cannot_disable_generation_bounds(settings, monkeypatch):
    settings.OLLAMA_REQUEST_TIMEOUT = 0
    settings.OLLAMA_MAX_TOKENS = -1
    settings.OLLAMA_NUM_THREADS = 0
    settings.OLLAMA_CONTEXT_WINDOW = -1
    constructor = MagicMock()
    monkeypatch.setattr('ai.providers.ollama_client.ollama.Client', constructor)
    client = OllamaClient()
    constructor.assert_called_once_with(host=settings.LLM_API_ENDPOINT, timeout=60)
    client.generate('Question', max_tokens=-1)
    assert constructor.return_value.chat.call_args.kwargs['options'] == {'temperature': 0.3, 'num_predict': 512}
