"""教師端工具：將明文 quiz.csv 轉換為加密版 quiz_enc.csv。

用法：
    python build_encrypted_quiz.py

輸入：quiz.csv（明文，含 answer / explanation 欄位）
輸出：quiz_enc.csv（answer → salted SHA-256 hash，explanation → XOR + base64）

加密方式：
  - answer：SHA-256( SALT + id + answer )，學生打開 CSV 只看到 hash
  - explanation：XOR 逐 byte 混淆後 base64 編碼，考完才由程式解碼顯示
"""
from __future__ import annotations

import base64
import csv
import hashlib
import os

# ── 與 quiz_tk.py 共用的密鑰，修改後需重新 build ──
SALT = "iSpan_DA_2025"
XOR_KEY = "pythonDA"


def hash_answer(qid: str, answer: str) -> str:
    """Salted SHA-256 hash for answer verification."""
    raw = f"{SALT}{qid}{answer.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def xor_encode(text: str, key: str = XOR_KEY) -> str:
    """XOR each byte with a repeating key, then base64 encode."""
    data = text.encode("utf-8")
    key_bytes = key.encode("utf-8")
    xored = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data))
    return base64.b64encode(xored).decode("ascii")


def main() -> None:
    src = os.path.join(os.path.dirname(__file__), "quiz.csv")
    dst = os.path.join(os.path.dirname(__file__), "quiz_enc.csv")

    with open(src, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not fieldnames:
        raise SystemExit("quiz.csv is empty or has no header")

    for row in rows:
        row["answer"] = hash_answer(row["id"], row["answer"])
        if row.get("explanation"):
            row["explanation"] = xor_encode(row["explanation"])

    with open(dst, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done. {len(rows)} questions encrypted -> {dst}")


if __name__ == "__main__":
    main()
