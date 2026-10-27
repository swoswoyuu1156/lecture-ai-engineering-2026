from types import SimpleNamespace
from unittest.mock import Mock
from app import ask


def test_day1_chat_keeps_history(monkeypatch):
    response = SimpleNamespace(
        text="青色です",
        usage_metadata=None,
    )
    chat = SimpleNamespace(
        send_message=Mock(return_value=response),
    )
    create = Mock(return_value=chat)
    client = SimpleNamespace(
        chats=SimpleNamespace(create=create),
    )

    monkeypatch.setattr(ask.genai, "Client", lambda api_key: client)
    monkeypatch.setattr(ask, "get_api_key", lambda: "dummy-key")

    messages = iter(["私は青色が好きです", "好きな色は？", "exit"])
    monkeypatch.setattr(
        "builtins.input", lambda prompt: next(messages)
    )

    ask.day1_chat()

    create.assert_called_once_with(model=ask.MODEL)
    assert chat.send_message.call_count == 2
    assert chat.send_message.call_args_list[0].args[0] == "私は青色が好きです"
    assert chat.send_message.call_args_list[1].args[0] == "好きな色は？"
