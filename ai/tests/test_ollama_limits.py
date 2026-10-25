from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

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


def test_structured_generation_forwards_schema_and_deterministic_options(monkeypatch):
    constructor = MagicMock()
    constructor.return_value.chat.return_value = SimpleNamespace(
        message=SimpleNamespace(content='{"names":["Alice"]}'), done_reason='stop',
    )
    monkeypatch.setattr('ai.providers.ollama_client.ollama.Client', constructor)
    schema = {'type': 'object', 'properties': {'names': {'type': 'array', 'items': {'type': 'string'}}}}
    result = OllamaClient().generate(
        'Extract names.', context='Alice signed.', temperature=0, seed=0, json_schema=schema,
        examples=[{'document': 'Bob paid.', 'response': {'names': ['Bob']}}],
    )
    assert result == '{"names":["Alice"]}'
    request = constructor.return_value.chat.call_args.kwargs
    assert request['format'] == schema
    assert request['options']['temperature'] == request['options']['seed'] == 0
    assert request['options']['num_predict'] > 0
    assert request['messages'] == [
        {'role': 'system', 'content': 'Extract names.'},
        {'role': 'user', 'content': 'Bob paid.'},
        {'role': 'assistant', 'content': '{"names": ["Bob"]}'},
        {'role': 'user', 'content': 'Alice signed.'},
    ]


def test_truncated_structured_output_is_rejected_without_identical_retries(monkeypatch):
    constructor = MagicMock()
    constructor.return_value.chat.return_value = SimpleNamespace(
        message=SimpleNamespace(content='{"names":['), done_reason='length',
    )
    monkeypatch.setattr('ai.providers.ollama_client.ollama.Client', constructor)
    with pytest.raises(ValueError, match='token limit'):
        OllamaClient().generate('Extract.', json_schema={'type': 'object'})
    assert constructor.return_value.chat.call_count == 1
