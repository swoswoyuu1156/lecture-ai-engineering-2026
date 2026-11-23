import csv
import os
import re
import shutil
import statistics
import subprocess
import time
from pathlib import Path

folder = Path("lectures/01")
models = ["gemini-3.5-flash-lite", "gemini-3.6-flash"]
questions = {
    "LoRA": "LoRAとは何ですか？",
    "講座固有": "AIE2026の講座の宿題にある「3レベル」とは何ですか？",
}

records = []

# 2モデル x 2質問 x 2試行
for model in models:
    for category, question in questions.items():
        for trial in (1, 2):
            start = time.perf_counter()
            input_tokens = None
            output_tokens = None
            status = "未測定"

            try:
                result = subprocess.run(
                    ["uv", "run", "python", "-m", "app.ask", question],
                    env={**os.environ, "AIE_MODEL": model},
                    capture_output=True,
                    text=True,
                    timeout=40,
                )

                input_match = re.search(
                    r"\[usage\] input tokens:\s*(\d+)",
                    result.stdout,
                )
                output_match = re.search(
                    r"\[usage\] output tokens:\s*(\d+)",
                    result.stdout,
                )

                if input_match and output_match and result.returncode == 0:
                    input_tokens = int(input_match.group(1))
                    output_tokens = int(output_match.group(1))
                    status = "成功"
                else:
                    status = f"取得失敗（終了コード{result.returncode}）"

            except subprocess.TimeoutExpired:
                status = "タイムアウト"

            elapsed = round(time.perf_counter() - start, 3)

            records.append({
                "model": model,
                "question": category,
                "trial": trial,
                "status": status,
                "elapsed_seconds": elapsed,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            })

            print(
                f"{model} / {category} / {trial}: "
                f"{status}, {elapsed}秒, 出力={output_tokens}",
                flush=True,
            )
            time.sleep(6)

with (folder / "day1_advanced_results.csv").open(
    "w", encoding="utf-8-sig", newline=""
) as f:
    writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
    writer.writeheader()
    writer.writerows(records)


def result_table():
    lines = [
        "| モデル | 質問 | 回 | 状態 | 経過秒数 | 入力 | 出力 |",
        "|---|---|---:|---|---:|---:|---:|",
    ]
    for r in records:
        i = r["input_tokens"] if r["input_tokens"] is not None else "—"
        o = r["output_tokens"] if r["output_tokens"] is not None else "—"
        lines.append(
            f'| {r["model"]} | {r["question"]} | {r["trial"]} '
            f'| {r["status"]} | {r["elapsed_seconds"]:.3f} '
            f'| {i} | {o} |'
        )
    return "\n".join(lines)


def model_summary(model):
    data = [
        r for r in records
        if r["model"] == model and r["status"] == "成功"
    ]
    if not data:
        return "成功した測定なし"
    seconds = [r["elapsed_seconds"] for r in data]
    tokens = [r["output_tokens"] for r in data]
    return (
        f"成功{len(data)}/4件、"
        f"平均経過時間{statistics.mean(seconds):.3f}秒、"
        f"平均出力{statistics.mean(tokens):.1f}トークン"
    )


# 本物のAPIで会話履歴を動作確認
chat_result = "未確認"
try:
    run = subprocess.run(
        ["uv", "run", "python", "-m", "app.ask", "--chat"],
        input="私は青色が好きです。\n私の好きな色は何ですか？\nexit\n",
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "AIE_MODEL": models[0]},
    )
    replies = run.stdout.split("[chat reply] ")
    if run.returncode == 0 and len(replies) >= 3 and "青" in replies[2]:
        chat_result = "成功（2ターン目で前の発言を参照）"
    else:
        chat_result = "回答の内容を確認できず"
except subprocess.TimeoutExpired:
    chat_result = "タイムアウト"

# 既存の基礎課題は保持し、発展・実装の項目のみ置き換える
path = folder / "answer.md"
original = path.read_text(encoding="utf-8")
shutil.copy2(path, "/tmp/aie2026_day1_answer_before_advanced.md")

advanced_complete = all(
    any(
        r["status"] == "成功"
        and r["model"] == model
        and r["question"] == category
        for r in records
    )
    for model in models
    for category in questions
)

advanced_status = (
    "4条件すべてで計測成功"
    if advanced_complete else
    "一部測定失敗（詳細は結果表）"
)

section = f"""### 3. 発展課題：応答時間・トークン数の比較

**実施状況：{advanced_status}**

#### 実験方法

2種類のモデルと2種類の質問を組み合わせ、
各条件2回ずつ、合計8リクエストを実行した。
トークン数はGemini APIのusage_metadataから取得した。

経過時間はtime.perf_counterでPythonコマンドの開始から終了まで計測した。
これはPythonの起動、通信、モデル処理、SDK内部の再試行を含む
エンドツーエンド時間であり、モデルの純粋な推論時間ではない。

各呼び出しに40秒の制限を設定し、失敗もそのまま記録した。

#### 測定結果

{result_table()}

全結果のCSV：`lectures/01/day1_advanced_results.csv`

#### モデル別集計

- `gemini-3.5-flash-lite`：{model_summary(models[0])}
- `gemini-3.6-flash`：{model_summary(models[1])}

平均値は成功した試行のみで計算しているため、
失敗がある場合は比較に選択バイアスが生じうる。

#### レート制限・可用性についての考察

Google AI Studioで以前に確認した無料枠の表示では、
3.5 Flash LiteはRPM 15・RPD 500、
3.8 FlashはRPM 5・RPD 20だった。
これらは確認時点の表示であり、現在も同じとは限らない。
今回比較した3.6 Flashの上限は同じ値とは仮定できない。

以前の3.8 Flashでは、60秒以内に回答を取得できず
タイムアウトした。確認時の利用回数は上限未満だったため、
原因をレート制限と断定することはできない。

レート制限はRPM、TPM、RPDなどで評価されるため、
実運用では呼び出し間隔、使用量、タイムアウト、
エラー時の再試行方法を設計する必要がある。

#### 考察

出力トークン数と経過時間を両方測定することで、
モデルの比較には回答品質以外の指標も必要だと分かった。
ただし、通信時間やモデルの負荷などの条件を完全には
統一できていないため、今回の少数の試行だけで
モデル間の一般的な性能差を断定することはできない。

### 4. 実装課題：会話履歴を保持する機能

**実施状況：実装・自動テスト実施**

`app/ask.py`に`--chat`オプションを追加した。
Google Gen AI SDKの`client.chats.create()`でセッションを作成し、
同じセッションの`send_message()`を繰り返し使う構成とした。

これにより、前のメッセージを含む会話として続けて質問できる。
`exit`または`quit`で終了でき、従来の単発質問機能も残した。

`tests/test_day1_chat.py`では、同じChatオブジェクトが
2回の質問に使われることをモックで確認した。
既存テストと追加テストがすべて成功した。

実際のAPIによる会話テスト：**{chat_result}**

モックテストはプログラムの構造を検証するものであり、
実際のモデルが常に会話内容を正しく参照できる保証ではない。

"""

pattern = r"(?ms)^### 3\. 発展課題.*?(?=^## 気づき・疑問|\Z)"
if re.search(pattern, original):
    updated = re.sub(pattern, lambda _: section, original, count=1)
else:
    updated = original.rstrip() + "\n\n" + section

updated = re.sub(
    r"(?m)^- \*\*取り組んだレベル：\*\*.*$",
    "- **取り組んだレベル：** 基礎・発展・実装",
    updated,
)
updated = re.sub(
    r"(?m)^- \*\*追加の取り組み予定：\*\*.*\n?",
    "",
    updated,
)

path.write_text(updated, encoding="utf-8")

q3 = (
    "基礎では2種類のモデルと2種類の質問を用いて計12回の回答を比較し、"
    "出力の揺らぎと講座固有の知識に関する誤回答を分析した。"
    "発展では8回のAPI呼び出しを自動計測し、応答時間・トークン数・"
    "失敗時の挙動を記録した。"
    "実装では既存の単発質問機能を維持しながら会話履歴機能を追加し、"
    "自動テストを行った。"
    "特に計測結果の再現性と失敗事例を含めた考察を評価していただきたい。"
)

(folder / "day1_q3.txt").write_text(q3, encoding="utf-8")

print("\n=== 作業結果 ===")
print(f"発展課題: {advanced_status}")
print(f"実API会話テスト: {chat_result}")
print(f"Q3（{len(q3)}文字）: {q3}")

if advanced_complete:
    print("Q1: 発展｜Advanced")
else:
    print("Q1: 発展の測定結果に失敗条件があります。提出前に確認してください。")
