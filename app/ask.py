"""第1回: 素のLLMに1回だけ質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする

ツールも会話履歴も持たない「素の」呼び出し。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse

from google import genai
from google.genai import errors

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"


def ask(question: str) -> str:
    client = genai.Client(api_key=get_api_key())
    response = client.models.generate_content(model=MODEL, contents=question)

    usage = response.usage_metadata
    if usage is not None:
        print(f"[usage] input tokens: {usage.prompt_token_count}")
        print(f"[usage] output tokens: {usage.candidates_token_count}")

    return response.text



def day1_chat() -> None:
    """同じChatセッションで会話履歴を保持する。"""
    client = genai.Client(api_key=get_api_key())
    chat = client.chats.create(model=MODEL)
    print("[chat] 会話開始（exitで終了）")

    while True:
        try:
            question = input("あなた> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n会話終了")
            break

        if question.lower() in ("exit", "quit"):
            print("会話終了")
            break
        if not question:
            continue

        try:
            response = chat.send_message(question)
        except errors.APIError as e:
            print(api_error_message(e.code, e.message))
            continue

        print(f"[chat reply] {response.text}")
        usage = response.usage_metadata
        if usage is not None:
            print(f"[usage] input tokens: {usage.prompt_token_count}")
            print(f"[usage] output tokens: {usage.candidates_token_count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--chat", action="store_true", help="会話履歴を保持して連続質問する")
    args = parser.parse_args()
    if args.chat:
        day1_chat()
        return

    print(f"[model] {MODEL}")
    print(f"[質問] {args.question}\n")
    try:
        print(ask(args.question))
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
