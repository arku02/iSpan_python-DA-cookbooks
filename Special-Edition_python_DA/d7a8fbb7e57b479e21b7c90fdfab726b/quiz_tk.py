"""Python 資料分析能力評量 — Tkinter 離線版（復古 PC 風格）。

啟動方式：
    python quiz_tk.py

需求：Python 3.10+（僅使用標準庫，不需安裝任何套件）。
"""
from __future__ import annotations

import base64
import csv
import hashlib
import math
import os
import random
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import font as tkfont
from tkinter import messagebox, ttk
from typing import Any

# ── 常數 ──────────────────────────────────────────────
QUIZ_CSV = os.path.join(os.path.dirname(__file__), "quiz_enc.csv")
RESULT_CSV_V2 = os.path.join(os.path.dirname(__file__), "result_log_v2.csv")
CONFIG_JSON = os.path.join(os.path.dirname(__file__), "class_config.json")
EXAM_DURATION_SEC = 30 * 60  # 30 分鐘
DIFFICULTY_WEIGHT = {"簡單": 1, "中等": 2, "困難": 3}

# ── 色彩（復古 PC / Windows 95 風格）────────────────
BG = "#C0C0C0"
CARD_BG = "#D4D0C8"
HEADER_BG = "#000080"
HEADER_FG = "#FFFFFF"
PRIMARY = "#000080"
ACCENT = "#008080"
SUCCESS = "#008000"
WARNING = "#808000"
DANGER = "#800000"
MARKED_COLOR = "#FFFF00"
ANSWERED_BG = "#87CEEB"
UNANSWERED_BG = "#A0A0A0"
BORDER = "#808080"
TEXT = "#000000"
TEXT_LIGHT = "#404040"
CORRECT_BG = "#90EE90"
WRONG_BG = "#FFB6C1"
BTN_FACE = "#D4D0C8"

# 類別英文鍵（用於 CSV 欄位名與雷達圖軸）
CAT_KEYS = ["NumPy", "Pandas", "Python基礎", "數據分析概念", "資料視覺化"]
CAT_CSV_KEYS = ["cat_numpy", "cat_pandas", "cat_python", "cat_concept", "cat_viz"]
TYPE_KEYS = ["概念題", "函數應用題", "代碼執行題", "代碼理解題", "語法題"]
TYPE_CSV_KEYS = ["type_concept", "type_function", "type_execution", "type_understanding", "type_syntax"]
DIFF_ORDER = ["簡單", "中等", "困難"]


# ── 加密常數（須與 build_encrypted_quiz.py ��致）────
_SALT = "iSpan_DA_2025"
_XOR_KEY = "pythonDA"


def _hash_answer(qid: str, answer: str) -> str:
    raw = f"{_SALT}{qid}{answer.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _xor_decode(encoded: str, key: str = _XOR_KEY) -> str:
    data = base64.b64decode(encoded)
    key_bytes = key.encode("utf-8")
    return bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data)).decode("utf-8")


# ── 讀取題庫 ─────────��────────────────────────────���───
def load_questions(path: str = QUIZ_CSV) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ── 計分 ──────────────────────────────────────────────
def evaluate(
    questions: list[dict], responses: dict[int, str]
) -> tuple[float, list[dict], dict]:
    total_weight = sum(DIFFICULTY_WEIGHT.get(q["difficulty"], 1) for q in questions)
    diff_stats: dict[str, dict] = {}
    results = []
    score = 0.0

    for q in questions:
        qid = int(q["id"])
        diff = q["difficulty"]
        w = DIFFICULTY_WEIGHT.get(diff, 1)
        q_score = (w / total_weight) * 100

        if diff not in diff_stats:
            diff_stats[diff] = {"count": 0, "correct": 0, "points": 0.0, "max": 0.0}
        diff_stats[diff]["count"] += 1
        diff_stats[diff]["max"] += q_score

        selected = responses.get(qid, "")
        answer_hash = q["answer"].strip()
        # Compare by hashing the student's selection with the same salt
        is_correct = (
            _hash_answer(str(qid), selected) == answer_hash
            if selected
            else False
        )
        # Determine the correct letter by brute-force checking a/b/c
        correct = ""
        for opt in ("a", "b", "c"):
            if _hash_answer(str(qid), opt) == answer_hash:
                correct = opt
                break

        if is_correct:
            score += q_score
            diff_stats[diff]["correct"] += 1
            diff_stats[diff]["points"] += q_score

        results.append(
            {
                "id": qid,
                "question": q["question"],
                "option_a": q["option_a"],
                "option_b": q["option_b"],
                "option_c": q["option_c"],
                "selected": selected,
                "correct": correct,
                "is_correct": is_correct,
                "difficulty": diff,
                "explanation": _xor_decode(q["explanation"]) if q.get("explanation") else "",
                "knowledge_point": q.get("knowledge_point", ""),
                "chapter": q.get("chapter", ""),
                "category": q.get("category", ""),
                "question_type": q.get("question_type", ""),
                "q_score": q_score,
            }
        )

    return round(score, 1), results, diff_stats


# ── 聚合學習狀況 ─────────────────────────────────────
def summarize(
    results: list[dict],
    q_elapsed: dict[int, float],
    duration_sec: float,
) -> dict[str, Any]:
    total_correct = sum(1 for r in results if r["is_correct"])
    answered = sum(1 for r in results if r["selected"])
    avg_sec = duration_sec / len(results) if results else 0.0

    cat_stats: dict[str, dict] = {}
    for r in results:
        cat = r.get("category", "其他")
        if cat not in cat_stats:
            cat_stats[cat] = {"correct": 0, "total": 0, "rate": 0.0}
        cat_stats[cat]["total"] += 1
        if r["is_correct"]:
            cat_stats[cat]["correct"] += 1
    for v in cat_stats.values():
        v["rate"] = v["correct"] / v["total"] if v["total"] else 0.0

    type_stats: dict[str, dict] = {}
    for r in results:
        qt = r.get("question_type", "其他")
        if qt not in type_stats:
            type_stats[qt] = {"correct": 0, "total": 0, "rate": 0.0}
        type_stats[qt]["total"] += 1
        if r["is_correct"]:
            type_stats[qt]["correct"] += 1
    for v in type_stats.values():
        v["rate"] = v["correct"] / v["total"] if v["total"] else 0.0

    diff_stats: dict[str, dict] = {}
    for r in results:
        d = r["difficulty"]
        if d not in diff_stats:
            diff_stats[d] = {"correct": 0, "total": 0, "rate": 0.0}
        diff_stats[d]["total"] += 1
        if r["is_correct"]:
            diff_stats[d]["correct"] += 1
    for v in diff_stats.values():
        v["rate"] = v["correct"] / v["total"] if v["total"] else 0.0

    chap_wrong: dict[str, int] = {}
    for r in results:
        if not r["is_correct"]:
            ch = r.get("chapter", "")
            if ch:
                chap_wrong[ch] = chap_wrong.get(ch, 0) + 1
    chap_wrong_sorted = sorted(chap_wrong.items(), key=lambda x: x[1], reverse=True)[:5]

    kp_wrong: dict[str, tuple[int, str]] = {}
    for r in results:
        if not r["is_correct"]:
            kp = r.get("knowledge_point", "")
            ch = r.get("chapter", "")
            if kp:
                cnt, _ = kp_wrong.get(kp, (0, ch))
                kp_wrong[kp] = (cnt + 1, ch)
    kp_wrong_sorted = sorted(kp_wrong.items(), key=lambda x: x[1][0], reverse=True)[:3]

    slowest = sorted(q_elapsed.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_correct": total_correct,
        "answered": answered,
        "duration_sec": duration_sec,
        "avg_sec_per_q": avg_sec,
        "cat_stats": cat_stats,
        "type_stats": type_stats,
        "diff_stats": diff_stats,
        "chap_wrong": chap_wrong_sorted,
        "kp_wrong": [(kp, cnt, ch) for kp, (cnt, ch) in kp_wrong_sorted],
        "slowest_qs": slowest,
    }


# ── 儲存結果（v2 schema）────────────────────────────
def save_result(
    name: str, class_name: str, exam_id: str, score: float,
    responses: dict[int, str], total_q: int,
    summary: dict[str, Any], marked: set[int],
) -> None:
    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"
    correct_rate = round(summary["total_correct"] / total_q * 100, 1) if total_q else 0

    row: dict[str, Any] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": name, "class": class_name, "exam_id": exam_id,
        "score": score, "total": 100, "correct_rate": correct_rate, "grade": grade,
        "duration_sec": round(summary["duration_sec"], 1),
        "avg_sec_per_q": round(summary["avg_sec_per_q"], 1),
    }
    for cat_key, csv_key in zip(CAT_KEYS, CAT_CSV_KEYS):
        row[f"{csv_key}_rate"] = round(summary["cat_stats"].get(cat_key, {}).get("rate", 0.0) * 100, 1)
    for d in DIFF_ORDER:
        key = {"簡單": "easy", "中等": "medium", "困難": "hard"}[d]
        row[f"diff_{key}_rate"] = round(summary["diff_stats"].get(d, {}).get("rate", 0.0) * 100, 1)
    for type_key, csv_key in zip(TYPE_KEYS, TYPE_CSV_KEYS):
        row[f"{csv_key}_rate"] = round(summary["type_stats"].get(type_key, {}).get("rate", 0.0) * 100, 1)
    row["marked_count"] = len(marked)
    row["marked_ids"] = ";".join(str(m) for m in sorted(marked))
    for i in range(3):
        kp = summary.get("kp_wrong", [])
        row[f"top_weak_kp_{i+1}"] = kp[i][0] if i < len(kp) else ""
    for i in range(1, total_q + 1):
        row[f"q{i}"] = responses.get(i, "")

    file_exists = os.path.isfile(RESULT_CSV_V2)
    with open(RESULT_CSV_V2, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys(), quoting=csv.QUOTE_ALL)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# ── HTML 報告產生 ─────────────────────────────────────
def generate_html_report(
    name: str, class_name: str, exam_id: str, score: float,
    results: list[dict], summary: dict, marked: set[int],
) -> str:
    """產生自包含 HTML 報告，回傳檔案路徑。"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in name if c.isalnum() or c in "_ -")
    filepath = os.path.join(os.path.dirname(__file__), f"report_{safe_name}_{ts}.html")

    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"
    dur = summary["duration_sec"]
    dur_m, dur_s = divmod(int(dur), 60)
    total_q = len(results)
    total_correct = summary["total_correct"]

    # SVG 雷達圖
    cx, cy, r_max = 160, 170, 120
    cats = CAT_KEYS
    n = len(cats)
    angles = [math.pi / 2 + 2 * math.pi * i / n for i in range(n)]
    short_names = {"NumPy": "NumPy", "Pandas": "Pandas", "Python基礎": "Python",
                   "數據分析概念": "概念", "資料視覺化": "視覺化"}

    grid_lines = ""
    for lv in (0.25, 0.5, 0.75, 1.0):
        pts = " ".join(f"{cx + r_max*lv*math.cos(a):.1f},{cy - r_max*lv*math.sin(a):.1f}" for a in angles)
        grid_lines += f'<polygon points="{pts}" fill="none" stroke="#ccc" />\n'
    axis_lines = ""
    for a in angles:
        axis_lines += f'<line x1="{cx}" y1="{cy}" x2="{cx+r_max*math.cos(a):.1f}" y2="{cy-r_max*math.sin(a):.1f}" stroke="#ccc"/>\n'

    cs = summary["cat_stats"]
    data_pts = " ".join(
        f"{cx + r_max*cs.get(c,{}).get('rate',0)*math.cos(angles[i]):.1f},{cy - r_max*cs.get(c,{}).get('rate',0)*math.sin(angles[i]):.1f}"
        for i, c in enumerate(cats)
    )
    labels_svg = ""
    for i, c in enumerate(cats):
        rate = cs.get(c, {}).get("rate", 0)
        lr = r_max + 30
        x = cx + lr * math.cos(angles[i])
        y = cy - lr * math.sin(angles[i])
        labels_svg += f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="middle" font-size="11">{short_names.get(c,c)} {rate*100:.0f}%</text>\n'

    radar_svg = f'''<svg width="320" height="340" style="background:#f0f0f0;border:1px solid #808080">
{grid_lines}{axis_lines}
<polygon points="{data_pts}" fill="rgba(0,0,128,0.25)" stroke="#000080" stroke-width="2"/>
{labels_svg}</svg>'''

    # 題型條形
    ts_data = summary["type_stats"]
    type_rows = ""
    for qt in TYPE_KEYS:
        if qt not in ts_data:
            continue
        st = ts_data[qt]
        pct = st["rate"] * 100
        type_rows += f'<tr><td>{qt}</td><td><div style="background:#a0a0a0;width:200px;height:16px;display:inline-block"><div style="background:#000080;width:{pct*2:.0f}px;height:16px"></div></div></td><td>{pct:.0f}% ({st["correct"]}/{st["total"]})</td></tr>\n'

    # 難度
    diff_rows = ""
    ds = summary["diff_stats"]
    for d in DIFF_ORDER:
        if d not in ds:
            continue
        s = ds[d]
        diff_rows += f'<tr><td>{d}</td><td>{s["correct"]}/{s["total"]}</td><td>{s["rate"]*100:.0f}%</td></tr>\n'

    # 弱點
    weak_html = ""
    for i, (kp, cnt, ch) in enumerate(summary.get("kp_wrong", []), 1):
        weak_html += f"<li>{kp}（章節: {ch}，錯 {cnt} 題）</li>\n"

    # 明細
    detail_rows = ""
    for r in results:
        cls = "correct" if r["is_correct"] else "wrong"
        sel = r["selected"] or "未作答"
        opts = {"a": r["option_a"], "b": r["option_b"], "c": r["option_c"]}
        sel_t = f'{sel.upper()}. {opts.get(sel, "")}' if sel in opts else sel
        cor_t = f'{r["correct"].upper()}. {opts.get(r["correct"], "")}'
        mark = " [標記]" if r["id"] in marked else ""
        q_text = r["question"].replace("\n", "<br>")
        detail_rows += f'''<tr class="{cls}"><td>{r["id"]}{mark}</td><td>{r["difficulty"]}</td>
<td style="text-align:left">{q_text}</td><td>{sel_t}</td><td>{cor_t}</td>
<td style="text-align:left;font-size:11px">{r["explanation"]}</td></tr>\n'''

    html = f"""<!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="UTF-8">
<title>測驗報告 - {name}</title>
<style>
body {{ font-family: "PingFang TC","Microsoft JhengHei",sans-serif; background:#c0c0c0; margin:20px; }}
.panel {{ background:#d4d0c8; border:2px outset #fff; padding:15px; margin-bottom:10px; }}
.header {{ background:#000080; color:#fff; padding:12px 20px; font-size:18px; font-weight:bold; }}
table {{ border-collapse:collapse; width:100%; font-size:13px; }}
th,td {{ border:1px solid #808080; padding:5px 8px; text-align:center; }}
th {{ background:#000080; color:#fff; }}
tr.correct {{ background:#90ee90; }}
tr.wrong {{ background:#ffb6c1; }}
.score-box {{ display:inline-block; text-align:center; padding:10px 25px; margin:5px; border:2px inset #808080; background:#d4d0c8; }}
.score-box .val {{ font-size:22px; font-weight:bold; }}
.score-box .lbl {{ font-size:11px; color:#404040; }}
ol {{ padding-left:20px; }}
</style></head><body>
<div class="header">Python 資料分析能力評量 — 測驗報告</div>
<div class="panel">
<b>姓名:</b> {name} &nbsp; <b>班級:</b> {class_name} &nbsp; <b>准考證號:</b> {exam_id or "—"}
&nbsp; <b>日期:</b> {datetime.now().strftime("%Y-%m-%d %H:%M")}
&nbsp; <b>作答時間:</b> {dur_m} 分 {dur_s} 秒
</div>
<div class="panel">
<div class="score-box"><div class="lbl">總分</div><div class="val">{score}/100</div></div>
<div class="score-box"><div class="lbl">等第</div><div class="val">{grade}</div></div>
<div class="score-box"><div class="lbl">答對</div><div class="val">{total_correct}/{total_q}</div></div>
<div class="score-box"><div class="lbl">平均每題</div><div class="val">{summary["avg_sec_per_q"]:.1f}s</div></div>
<div class="score-box"><div class="lbl">{"通過" if score>=60 else "未通過"}</div><div class="val">{"PASS" if score>=60 else "FAIL"}</div></div>
</div>
<div class="panel" style="display:flex;gap:20px;flex-wrap:wrap;">
<div><h3>能力輪廓</h3>{radar_svg}</div>
<div style="flex:1"><h3>難度階梯</h3>
<table><tr><th>難度</th><th>答對/總數</th><th>正確率</th></tr>{diff_rows}</table>
<h3 style="margin-top:12px">題型診斷</h3>
<table><tr><th>題型</th><th>進度</th><th>正確率</th></tr>{type_rows}</table>
</div>
</div>
<div class="panel">
<h3>需加強 TOP 3</h3>
<ol>{weak_html if weak_html else "<li>無</li>"}</ol>
</div>
<div class="panel">
<h3>答題明細</h3>
<table><tr><th>題號</th><th>難度</th><th style="width:40%">題目</th><th>你的答案</th><th>正確答案</th><th>解析</th></tr>
{detail_rows}</table>
</div>
<div style="text-align:center;color:#808080;font-size:11px;margin-top:10px;">
Python 資料分析能力評量系統 — 自動產生報告</div>
</body></html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return filepath


# ══════════════════════════════════════════════════════
#  GUI
# ══════════════════════════════════════════════════════
class QuizApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Python 資料分析能力評量")
        self.geometry("1020x740")
        self.configure(bg=BG)
        self.resizable(True, True)

        self.font_title = tkfont.Font(family="PingFang TC", size=18, weight="bold")
        self.font_heading = tkfont.Font(family="PingFang TC", size=13, weight="bold")
        self.font_body = tkfont.Font(family="PingFang TC", size=12)
        self.font_small = tkfont.Font(family="PingFang TC", size=10)
        self.font_code = tkfont.Font(family="Menlo", size=11)
        self.font_btn = tkfont.Font(family="PingFang TC", size=11, weight="bold")
        self.font_nav = tkfont.Font(family="Menlo", size=9)
        self.font_badge = tkfont.Font(family="PingFang TC", size=10, weight="bold")

        self.questions = load_questions()
        random.shuffle(self.questions)
        self.responses: dict[int, str] = {}
        self.name = ""
        self.class_name = ""
        self.exam_id = ""
        self.start_time = 0.0
        self.timer_id: str | None = None

        self.marked: set[int] = set()
        self.q_elapsed: dict[int, float] = {}
        self.q_last_enter: float = 0.0
        self._wheel_bound: bool = False
        self._active_scroll_canvas: tk.Canvas | None = None
        self._detail_filter: str = "all"

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)
        self._show_login()

    # ── macOS-safe 按鈕（Label-based）────────────────
    def _make_btn(self, parent: tk.Widget, text: str, command: Any,
                  bg: str = BTN_FACE, fg: str = TEXT,
                  font: Any = None, padx: int = 12, pady: int = 4) -> tk.Label:
        lbl = tk.Label(parent, text=f" {text} ", bg=bg, fg=fg,
                       font=font or self.font_btn,
                       relief="raised", bd=2, padx=padx, pady=pady, cursor="hand2")
        lbl._enabled = True  # type: ignore[attr-defined]
        lbl._cmd = command  # type: ignore[attr-defined]

        def _click(e: Any) -> None:
            if not lbl._enabled:  # type: ignore[attr-defined]
                return
            lbl.config(relief="sunken")
            lbl.after(80, lambda: lbl.config(relief="raised"))
            lbl._cmd()  # type: ignore[attr-defined]

        lbl.bind("<Button-1>", _click)
        return lbl

    def _btn_set_enabled(self, lbl: tk.Label, enabled: bool) -> None:
        lbl._enabled = enabled  # type: ignore[attr-defined]
        if enabled:
            lbl.config(fg=TEXT, relief="raised", cursor="hand2")
        else:
            lbl.config(fg="#808080", relief="groove", cursor="arrow")

    # ── 滾輪 helper ──────────────────────────────────
    def _enable_mousewheel(self, canvas: tk.Canvas) -> None:
        self._active_scroll_canvas = canvas
        if not self._wheel_bound:
            self.bind_all("<MouseWheel>", self._on_mousewheel)
            self._wheel_bound = True

    def _disable_mousewheel(self) -> None:
        if self._wheel_bound:
            self.unbind_all("<MouseWheel>")
            self._wheel_bound = False
        self._active_scroll_canvas = None

    def _on_mousewheel(self, event: Any) -> None:
        c = self._active_scroll_canvas
        if c is not None:
            try:
                c.yview_scroll(-1 * event.delta, "units")
            except tk.TclError:
                pass

    # ── 登入畫面 ──────────────────────────────────────
    def _show_login(self) -> None:
        self._clear()
        frame = tk.Frame(self.container, bg=BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        # 標題列（深藍）
        title_bar = tk.Frame(frame, bg=HEADER_BG, padx=10, pady=6)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="Python 資料分析能力評量", font=self.font_title,
                 bg=HEADER_BG, fg=HEADER_FG).pack()

        card = tk.Frame(frame, bg=CARD_BG, padx=40, pady=25, bd=2, relief="ridge")
        card.pack()

        tk.Label(card, text="考生資訊", font=self.font_heading,
                 bg=CARD_BG, fg=TEXT).grid(row=0, column=0, columnspan=2, pady=(0, 12))

        for row_idx, (label_text, attr_name) in enumerate([
            ("姓名", "entry_name"),
            ("班級", "entry_class"),
            ("准考證號（選填）", "entry_exam_id"),
        ], start=1):
            tk.Label(card, text=label_text, font=self.font_body, bg=CARD_BG, fg=TEXT
                     ).grid(row=row_idx, column=0, sticky="e", padx=(0, 10), pady=5)
            entry = tk.Entry(card, font=self.font_body, width=20, bd=2, relief="sunken")
            entry.grid(row=row_idx, column=1, pady=5)
            setattr(self, attr_name, entry)

        btn = self._make_btn(card, "開始作答", self._start_quiz, bg=PRIMARY, fg="white")
        btn.grid(row=4, column=0, columnspan=2, pady=(18, 0))

        # 作答須知
        notice = tk.Frame(frame, bg=CARD_BG, bd=2, relief="groove", padx=12, pady=8)
        notice.pack(fill="x", pady=(8, 0))
        tk.Label(notice, text="作答須知", font=self.font_badge,
                 bg=CARD_BG, fg=DANGER).pack(anchor="w")
        for n in [
            "1. 本測驗共 100 題，採分層計分（簡易 1x、中等 2x、困難 3x 權重）",
            "2. 可使用「標記本題」功能標註需回頭檢查之題目",
            "3. 作答時間為 30 分鐘，時間到自動交卷",
        ]:
            tk.Label(notice, text=n, font=self.font_small,
                     bg=CARD_BG, fg=TEXT_LIGHT, anchor="w").pack(anchor="w")

        self.entry_name.focus_set()

    # ── 開始測驗 ──────────────────────────────────────
    def _start_quiz(self) -> None:
        name = self.entry_name.get().strip()
        cls = self.entry_class.get().strip()
        if not name or not cls:
            messagebox.showwarning("提示", "請填寫姓名與班級")
            return
        self.name = name
        self.class_name = cls
        self.exam_id = self.entry_exam_id.get().strip()
        self.responses = {}
        self.marked = set()
        self.q_elapsed = {}
        self.q_last_enter = 0.0
        self.start_time = time.time()
        self.current_q = 0
        self._show_quiz()

    # ── 測驗畫面 ──────────────────────────────────────
    def _show_quiz(self) -> None:
        self._clear()

        # === 頂部深藍欄 ===
        top = tk.Frame(self.container, bg=HEADER_BG, padx=12, pady=6)
        top.pack(fill="x")
        tk.Label(top, text="Python 資料分析能力評量", font=self.font_heading,
                 bg=HEADER_BG, fg=HEADER_FG).pack(side="left")
        self.lbl_timer = tk.Label(top, font=self.font_heading, bg=HEADER_BG, fg=HEADER_FG)
        self.lbl_timer.pack(side="right")
        tk.Label(top, text=f"{self.name} | {self.class_name}",
                 font=self.font_body, bg=HEADER_BG, fg=HEADER_FG).pack(side="right", padx=15)

        # === 主內容區 ===
        main_area = tk.Frame(self.container, bg=BG)
        main_area.pack(fill="both", expand=True, padx=6, pady=4)

        # ── 右側 nav grid（可滾動）──
        nav_outer = tk.Frame(main_area, bg=CARD_BG, bd=2, relief="ridge", width=170)
        nav_outer.pack(side="right", fill="y", padx=(4, 0))
        nav_outer.pack_propagate(False)

        tk.Label(nav_outer, text="題號狀態", font=self.font_badge,
                 bg=CARD_BG, fg=TEXT, relief="groove", bd=1).pack(fill="x", pady=(0, 4))

        # 可滾動 canvas 放 grid
        nav_scroll = tk.Frame(nav_outer, bg=CARD_BG)
        nav_scroll.pack(fill="both", expand=True)

        self._nav_canvas = tk.Canvas(nav_scroll, bg=CARD_BG, highlightthickness=0, width=140)
        nav_sb = tk.Scrollbar(nav_scroll, orient="vertical", command=self._nav_canvas.yview)
        self._nav_inner = tk.Frame(self._nav_canvas, bg=CARD_BG)

        self._nav_canvas.create_window((0, 0), window=self._nav_inner, anchor="nw")
        self._nav_canvas.configure(yscrollcommand=nav_sb.set)
        self._nav_inner.bind("<Configure>",
                             lambda e: self._nav_canvas.configure(scrollregion=self._nav_canvas.bbox("all")))

        nav_sb.pack(side="right", fill="y")
        self._nav_canvas.pack(side="left", fill="both", expand=True)

        # Label-based nav items（macOS 可見 bg）
        self.nav_labels: list[tk.Label] = []
        cols = 5
        for i in range(len(self.questions)):
            r_i, c_i = divmod(i, cols)
            lbl = tk.Label(self._nav_inner, text=str(i + 1), width=3,
                           font=self.font_nav, bg=UNANSWERED_BG, fg=TEXT,
                           relief="raised", bd=1, cursor="hand2")
            lbl.grid(row=r_i, column=c_i, padx=1, pady=1)
            idx = i
            lbl.bind("<Button-1>", lambda e, idx=idx: self._goto_question(idx))
            self.nav_labels.append(lbl)

        # 圖例
        legend = tk.Frame(nav_outer, bg=CARD_BG, bd=1, relief="groove")
        legend.pack(fill="x", pady=(4, 0))
        for color, label in [(ANSWERED_BG, "已答"), (MARKED_COLOR, "標記"), (UNANSWERED_BG, "未答")]:
            rf = tk.Frame(legend, bg=CARD_BG)
            rf.pack(anchor="w", padx=4, pady=1)
            tk.Label(rf, bg=color, width=2, relief="raised", bd=1).pack(side="left", padx=(0, 4))
            tk.Label(rf, text=label, font=self.font_small, bg=CARD_BG, fg=TEXT_LIGHT).pack(side="left")

        # ── 左側題目區 ──
        left = tk.Frame(main_area, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        self.q_card = tk.Frame(left, bg=CARD_BG, padx=20, pady=15, bd=2, relief="ridge")
        self.q_card.pack(fill="both", expand=True)

        # 題號標題列
        self.q_title_frame = tk.Frame(self.q_card, bg=CARD_BG)
        self.q_title_frame.pack(fill="x")
        self.lbl_q_number = tk.Label(self.q_title_frame, font=self.font_heading,
                                     bg=CARD_BG, fg=PRIMARY)
        self.lbl_q_number.pack(side="left")
        self.lbl_badge_diff = tk.Label(self.q_title_frame, font=self.font_badge, bg=CARD_BG)
        self.lbl_badge_diff.pack(side="left", padx=(10, 0))
        self.lbl_badge_cat = tk.Label(self.q_title_frame, font=self.font_badge, bg=CARD_BG)
        self.lbl_badge_cat.pack(side="left", padx=(5, 0))

        tk.Frame(self.q_card, bg=BORDER, height=1).pack(fill="x", pady=(6, 8))

        self.lbl_question = tk.Label(
            self.q_card, font=self.font_body, bg=CARD_BG, fg=TEXT,
            wraplength=620, justify="left", anchor="w",
        )
        self.lbl_question.pack(anchor="w", pady=(0, 5))

        self.txt_code = tk.Text(
            self.q_card, font=self.font_code, bg="#1E1E2E", fg="#CDD6F4",
            height=4, wrap="word", padx=10, pady=8, relief="sunken", bd=2,
        )

        # 選項（Label-based，macOS bg 可見）
        self.selected_var = tk.StringVar(value="")
        self.radio_frame = tk.Frame(self.q_card, bg=CARD_BG)
        self.radio_frame.pack(anchor="w", pady=(8, 0), fill="x")

        self.opt_labels: list[tk.Label] = []
        for opt in ("a", "b", "c"):
            ol = tk.Label(self.radio_frame, font=self.font_body, bg=CARD_BG, fg=TEXT,
                          anchor="w", wraplength=600, justify="left", padx=10, pady=5,
                          relief="raised", bd=2, cursor="hand2")
            ol.pack(anchor="w", pady=2, fill="x")
            ol.bind("<Button-1>", lambda e, o=opt: self._select_option(o))
            self.opt_labels.append(ol)

        # === 導覽列（緊貼題目卡下方）===
        bot = tk.Frame(left, bg=BG, pady=4)
        bot.pack(fill="x")

        self.btn_prev = self._make_btn(bot, "< 上一題", self._prev_q)
        self.btn_prev.pack(side="left")
        self.btn_clear_q = self._make_btn(bot, "清除本題", self._clear_current)
        self.btn_clear_q.pack(side="left", padx=(6, 0))
        self.btn_mark = self._make_btn(bot, "標記本題", self._toggle_mark)
        self.btn_mark.pack(side="left", padx=(6, 0))

        self.btn_submit = self._make_btn(bot, "交卷", self._confirm_submit, bg=DANGER, fg="white")
        self.btn_submit.pack(side="right")
        self.btn_next = self._make_btn(bot, "下一題 >", self._next_q)
        self.btn_next.pack(side="right", padx=(0, 6))

        # 快捷鍵提示
        hint = tk.Label(left, text="快捷鍵:  A/B/C 選擇  |  Enter 下一題  |  Space 標記  |  ←→ 切題  |  Backspace 清除",
                        font=self.font_small, bg=BG, fg=TEXT_LIGHT)
        hint.pack(anchor="w", pady=(2, 0))

        # === 鍵盤綁定 ===
        self.bind_all("<Return>", self._key_next)
        self.bind_all("<Right>", self._key_next)
        self.bind_all("<Left>", self._key_prev)
        self.bind_all("<space>", self._key_mark)
        self.bind_all("<BackSpace>", self._key_clear)
        self.bind_all("<Key-a>", lambda e: self._select_option("a"))
        self.bind_all("<Key-b>", lambda e: self._select_option("b"))
        self.bind_all("<Key-c>", lambda e: self._select_option("c"))
        self.bind_all("<Key-A>", lambda e: self._select_option("a"))
        self.bind_all("<Key-B>", lambda e: self._select_option("b"))
        self.bind_all("<Key-C>", lambda e: self._select_option("c"))

        self._render_question()
        self._tick()

    # ── 鍵盤快捷鍵 ─────────────────────────────────────
    def _key_next(self, event: Any = None) -> None:
        if self.current_q < len(self.questions) - 1:
            self._next_q()

    def _key_prev(self, event: Any = None) -> None:
        if self.current_q > 0:
            self._prev_q()

    def _key_mark(self, event: Any = None) -> None:
        self._toggle_mark()

    def _key_clear(self, event: Any = None) -> None:
        self._clear_current()

    # ── 選項點擊 ──────────────────────────────────────
    def _select_option(self, opt: str) -> None:
        self.selected_var.set(opt)
        qid = int(self.questions[self.current_q]["id"])
        self.responses[qid] = opt
        self._highlight_options()
        self._render_nav_grid()

    def _highlight_options(self) -> None:
        sel = self.selected_var.get()
        for ol, opt in zip(self.opt_labels, ("a", "b", "c")):
            if opt == sel:
                ol.config(bg=ANSWERED_BG, relief="sunken")
            else:
                ol.config(bg=CARD_BG, relief="raised")

    # ── 題目渲染 ──────────────────────────────────────
    def _render_question(self) -> None:
        q = self.questions[self.current_q]
        qid = int(q["id"])
        total = len(self.questions)
        idx = self.current_q

        answered_count = sum(1 for i in range(total) if int(self.questions[i]["id"]) in self.responses)
        self.lbl_q_number.config(text=f"第 {idx + 1} 題  ({answered_count}/{total} 已答)")

        diff = q["difficulty"]
        diff_colors = {"簡單": SUCCESS, "中等": WARNING, "困難": DANGER}
        self.lbl_badge_diff.config(text=f"[{diff}]", fg=diff_colors.get(diff, TEXT_LIGHT))
        self.lbl_badge_cat.config(text=f"[{q.get('category', '')}]", fg=ACCENT)

        parts = q["question"].split("\n\n", 1)
        self.lbl_question.config(text=parts[0])

        self.txt_code.pack_forget()
        if len(parts) > 1 and parts[1].strip():
            self.txt_code.pack(anchor="w", pady=(5, 5), fill="x")
            self.txt_code.config(state="normal")
            self.txt_code.delete("1.0", "end")
            self.txt_code.insert("1.0", parts[1].strip())
            self.txt_code.config(state="disabled", height=min(8, parts[1].count("\n") + 2))

        labels = {"a": q["option_a"], "b": q["option_b"], "c": q["option_c"]}
        for ol, opt in zip(self.opt_labels, ("a", "b", "c")):
            ol.config(text=f"  ({opt.upper()})  {labels[opt]}")

        prev = self.responses.get(qid, "")
        self.selected_var.set(prev)
        self._highlight_options()

        # 標記按鈕
        if qid in self.marked:
            self.btn_mark.config(text=" 取消標記 ", bg=MARKED_COLOR, fg=TEXT)
        else:
            self.btn_mark.config(text=" 標記本題 ", bg=BTN_FACE, fg=TEXT)

        self._render_nav_grid()

        self._btn_set_enabled(self.btn_prev, idx > 0)
        self._btn_set_enabled(self.btn_next, idx < total - 1)

        self.q_last_enter = time.time()

    def _render_nav_grid(self) -> None:
        idx = self.current_q
        for i, lbl in enumerate(self.nav_labels):
            bid = int(self.questions[i]["id"])
            is_current = (i == idx)
            is_answered = bid in self.responses
            is_marked = bid in self.marked

            if is_marked:
                bg = MARKED_COLOR
                fg = PRIMARY if is_answered else TEXT
            elif is_answered:
                bg = ANSWERED_BG
                fg = PRIMARY
            else:
                bg = UNANSWERED_BG
                fg = TEXT

            relief = "sunken" if is_current else "raised"
            bd = 2 if is_current else 1
            lbl.config(bg=bg, fg=fg, relief=relief, bd=bd)

    def _toggle_mark(self) -> None:
        qid = int(self.questions[self.current_q]["id"])
        if qid in self.marked:
            self.marked.discard(qid)
            self.btn_mark.config(text=" 標記本題 ", bg=BTN_FACE, fg=TEXT)
        else:
            self.marked.add(qid)
            self.btn_mark.config(text=" 取消標記 ", bg=MARKED_COLOR, fg=TEXT)
        self._render_nav_grid()

    def _clear_current(self) -> None:
        qid = int(self.questions[self.current_q]["id"])
        self.responses.pop(qid, None)
        self.selected_var.set("")
        self._highlight_options()
        self._render_nav_grid()
        total = len(self.questions)
        answered_count = sum(1 for i in range(total) if int(self.questions[i]["id"]) in self.responses)
        self.lbl_q_number.config(text=f"第 {self.current_q + 1} 題  ({answered_count}/{total} 已答)")

    def _goto_question(self, idx: int) -> None:
        self._save_current()
        self.current_q = idx
        self._render_question()

    def _prev_q(self) -> None:
        if self.current_q > 0:
            self._save_current()
            self.current_q -= 1
            self._render_question()

    def _next_q(self) -> None:
        if self.current_q < len(self.questions) - 1:
            self._save_current()
            self.current_q += 1
            self._render_question()

    def _save_current(self) -> None:
        if self.q_last_enter > 0:
            qid = int(self.questions[self.current_q]["id"])
            elapsed = time.time() - self.q_last_enter
            self.q_elapsed[qid] = self.q_elapsed.get(qid, 0.0) + elapsed
            self.q_last_enter = 0.0
        val = self.selected_var.get()
        if val:
            qid = int(self.questions[self.current_q]["id"])
            self.responses[qid] = val

    # ── 計時器 ────────────────────────────────────────
    def _tick(self) -> None:
        elapsed = time.time() - self.start_time
        remaining = max(0, EXAM_DURATION_SEC - int(elapsed))
        mins, secs = divmod(remaining, 60)
        self.lbl_timer.config(text=f"{mins:02d}:{secs:02d}")
        if remaining <= 60:
            self.lbl_timer.config(fg="#FF0000")
        else:
            self.lbl_timer.config(fg=HEADER_FG)
        if remaining <= 0:
            self._submit()
            return
        self.timer_id = self.after(1000, self._tick)

    # ── 交卷 ──────────────────────────────────────────
    def _confirm_submit(self) -> None:
        unanswered = sum(1 for q in self.questions if int(q["id"]) not in self.responses)
        msg = "確定要交卷嗎？"
        if unanswered > 0:
            msg += f"\n\n尚有 {unanswered} 題未作答。"
        if self.marked:
            msg += f"\n尚有 {len(self.marked)} 題標記待檢查。"
        if messagebox.askyesno("確認交卷", msg):
            self._submit()

    def _submit(self) -> None:
        self._save_current()
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None

        self.duration_total = time.time() - self.start_time
        score, results, diff_stats = evaluate(self.questions, self.responses)
        self._last_summary = summarize(results, self.q_elapsed, self.duration_total)
        self._last_results = results
        self._last_score = score
        save_result(self.name, self.class_name, self.exam_id,
                    score, self.responses, len(self.questions),
                    self._last_summary, self.marked)
        self._show_results(score, results, diff_stats, self._last_summary)

    # ── 雷達圖 ────────────────────────────────────────
    def _draw_radar(self, parent: tk.Widget, cat_stats: dict) -> tk.Canvas:
        size = 290
        cx, cy = size // 2, size // 2 + 10
        r_max = 110
        canvas = tk.Canvas(parent, width=size, height=size + 20,
                           bg=CARD_BG, highlightthickness=0, bd=2, relief="sunken")
        n = len(CAT_KEYS)
        angles = [math.pi / 2 + 2 * math.pi * i / n for i in range(n)]

        for level in (0.25, 0.5, 0.75, 1.0):
            pts = []
            for a in angles:
                pts.extend([cx + r_max * level * math.cos(a), cy - r_max * level * math.sin(a)])
            canvas.create_polygon(pts, outline="#808080", fill="", width=1)

        for a in angles:
            canvas.create_line(cx, cy, cx + r_max * math.cos(a),
                               cy - r_max * math.sin(a), fill="#808080")

        data_pts = []
        for i, cat in enumerate(CAT_KEYS):
            rate = cat_stats.get(cat, {}).get("rate", 0.0)
            data_pts.extend([cx + r_max * rate * math.cos(angles[i]),
                             cy - r_max * rate * math.sin(angles[i])])
        canvas.create_polygon(data_pts, outline=PRIMARY, fill=PRIMARY, width=2, stipple="gray25")

        short = {"NumPy": "NumPy", "Pandas": "Pandas", "Python基礎": "Python",
                 "數據分析概念": "概念", "資料視覺化": "視覺化"}
        for i, cat in enumerate(CAT_KEYS):
            rate = cat_stats.get(cat, {}).get("rate", 0.0)
            lr = r_max + 26
            x, y = cx + lr * math.cos(angles[i]), cy - lr * math.sin(angles[i])
            canvas.create_text(x, y, text=f"{short.get(cat, cat)}\n{rate*100:.0f}%",
                               font=self.font_small, fill=TEXT, justify="center")

        for i in range(0, len(data_pts), 2):
            canvas.create_oval(data_pts[i]-3, data_pts[i+1]-3,
                               data_pts[i]+3, data_pts[i+1]+3, fill=PRIMARY, outline="white")
        return canvas

    # ── 條形圖 ────────────────────────────────────────
    def _draw_hbar(self, parent: tk.Widget, type_stats: dict, width: int = 480) -> tk.Canvas:
        types = [t for t in TYPE_KEYS if t in type_stats]
        row_h, label_w = 30, 90
        bar_max = width - label_w - 110
        h = row_h * len(types) + 16
        canvas = tk.Canvas(parent, width=width, height=h,
                           bg=CARD_BG, highlightthickness=0, bd=2, relief="sunken")
        y = 8
        for qt in types:
            st = type_stats[qt]
            rate = st["rate"]
            canvas.create_text(label_w - 4, y + row_h // 2, text=qt,
                               font=self.font_small, fill=TEXT, anchor="e")
            canvas.create_rectangle(label_w, y + 4, label_w + bar_max, y + row_h - 4,
                                    fill=UNANSWERED_BG, outline=BORDER)
            fill_w = max(1, int(rate * bar_max))
            canvas.create_rectangle(label_w, y + 4, label_w + fill_w, y + row_h - 4,
                                    fill=PRIMARY, outline="")
            canvas.create_text(label_w + bar_max + 6, y + row_h // 2,
                               text=f"{rate*100:.0f}% ({st['correct']}/{st['total']})",
                               font=self.font_small, fill=TEXT, anchor="w")
            y += row_h
        return canvas

    # ── 結果畫面 ──────────────────────────────────────
    def _show_results(self, score: float, results: list[dict],
                      diff_stats: dict, summary_data: dict) -> None:
        self._clear()

        canvas = tk.Canvas(self.container, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        self._enable_mousewheel(canvas)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        # 頂欄
        dur_m, dur_s = divmod(int(summary_data["duration_sec"]), 60)
        hdr = tk.Frame(scroll_frame, bg=HEADER_BG, padx=15, pady=8)
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(hdr, text=f"成績單 | {self.name} | {self.class_name} | 作答 {dur_m}分{dur_s}秒",
                 font=self.font_heading, bg=HEADER_BG, fg=HEADER_FG).pack(side="left")
        # 下載按鈕
        dl_btn = self._make_btn(hdr, "下載報告", self._download_report, bg="#008080", fg="white")
        dl_btn.pack(side="right")

        # 總覽
        grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"
        passed = score >= 60
        total_correct = summary_data["total_correct"]
        total_q = len(results)
        color = SUCCESS if passed else DANGER

        overview = tk.Frame(scroll_frame, bg=CARD_BG, padx=15, pady=10, bd=2, relief="ridge")
        overview.pack(fill="x", pady=(0, 8))
        sf = tk.Frame(overview, bg=CARD_BG)
        sf.pack(fill="x")
        for lbl_t, val, c in [
            ("總分", f"{score}/100", color), ("等第", grade, color),
            ("通過", "PASS" if passed else "FAIL", color),
            ("答對", f"{total_correct}/{total_q}", TEXT),
            ("平均每題", f"{summary_data['avg_sec_per_q']:.1f}秒", TEXT),
        ]:
            box = tk.Frame(sf, bg=CARD_BG, bd=2, relief="sunken", padx=12, pady=4)
            box.pack(side="left", expand=True, padx=3)
            tk.Label(box, text=lbl_t, font=self.font_small, bg=CARD_BG, fg=TEXT_LIGHT).pack()
            tk.Label(box, text=val, font=self.font_heading, bg=CARD_BG, fg=c).pack()

        # 雷達 + 難度
        mid = tk.Frame(scroll_frame, bg=BG)
        mid.pack(fill="x", pady=(0, 8))

        rc = tk.Frame(mid, bg=CARD_BG, padx=8, pady=8, bd=2, relief="ridge")
        rc.pack(side="left", padx=(0, 4))
        tk.Label(rc, text="能力輪廓", font=self.font_badge, bg=CARD_BG, fg=TEXT).pack(anchor="w")
        self._draw_radar(rc, summary_data["cat_stats"]).pack()

        dc = tk.Frame(mid, bg=CARD_BG, padx=15, pady=8, bd=2, relief="ridge")
        dc.pack(side="left", fill="both", expand=True, padx=(4, 0))
        tk.Label(dc, text="難度階梯", font=self.font_badge, bg=CARD_BG, fg=TEXT).pack(anchor="w", pady=(0, 6))
        sd = summary_data["diff_stats"]
        diff_colors = {"簡單": SUCCESS, "中等": WARNING, "困難": DANGER}
        for dn in DIFF_ORDER:
            if dn not in sd:
                continue
            ds = sd[dn]
            pct = ds["rate"] * 100
            rf = tk.Frame(dc, bg=CARD_BG)
            rf.pack(fill="x", pady=3)
            tk.Label(rf, text=f"[{dn}]", font=self.font_body, bg=CARD_BG,
                     fg=diff_colors.get(dn, TEXT), width=5).pack(side="left")
            tk.Label(rf, text=f"{ds['correct']}/{ds['total']}題  {pct:.0f}%",
                     font=self.font_body, bg=CARD_BG, fg=TEXT).pack(side="left", padx=8)
            bar_f = tk.Frame(rf, bg=UNANSWERED_BG, height=14, width=180, bd=1, relief="sunken")
            bar_f.pack(side="left", padx=4)
            bar_f.pack_propagate(False)
            fw = int(180 * pct / 100)
            if fw > 0:
                tk.Frame(bar_f, bg=diff_colors.get(dn, PRIMARY), width=fw).pack(side="left", fill="y")

        # 題型診斷
        tc = tk.Frame(scroll_frame, bg=CARD_BG, padx=15, pady=8, bd=2, relief="ridge")
        tc.pack(fill="x", pady=(0, 8))
        tk.Label(tc, text="題型診斷", font=self.font_badge, bg=CARD_BG, fg=TEXT).pack(anchor="w", pady=(0, 4))
        self._draw_hbar(tc, summary_data["type_stats"]).pack(anchor="w")

        # 弱點分析
        wc = tk.Frame(scroll_frame, bg=CARD_BG, padx=15, pady=8, bd=2, relief="ridge")
        wc.pack(fill="x", pady=(0, 8))
        kp_wrong = summary_data.get("kp_wrong", [])
        chap_wrong = summary_data.get("chap_wrong", [])
        if kp_wrong:
            tk.Label(wc, text="需加強 TOP 3", font=self.font_badge, bg=CARD_BG, fg=DANGER).pack(anchor="w", pady=(0, 3))
            for i, (kp, cnt, ch) in enumerate(kp_wrong, 1):
                tk.Label(wc, text=f"  {i}. {kp} (章節: {ch}, 錯{cnt}題)",
                         font=self.font_body, bg=CARD_BG, fg=TEXT, anchor="w").pack(anchor="w")
        if chap_wrong:
            tk.Label(wc, text="章節錯題熱區", font=self.font_badge, bg=CARD_BG, fg=WARNING).pack(anchor="w", pady=(8, 3))
            for ch, cnt in chap_wrong:
                tk.Label(wc, text=f"  {ch} {'·'*min(cnt,20)} {cnt}錯",
                         font=self.font_small, bg=CARD_BG, fg=TEXT, anchor="w").pack(anchor="w")
        slowest = summary_data.get("slowest_qs", [])
        if slowest:
            tk.Label(wc, text="停留最久 TOP 5", font=self.font_badge, bg=CARD_BG, fg=TEXT_LIGHT).pack(anchor="w", pady=(8, 3))
            for qid, sec in slowest:
                rm = next((r for r in results if r["id"] == qid), None)
                st = "正確" if rm and rm["is_correct"] else "錯誤"
                tk.Label(wc, text=f"  第{qid}題: {sec:.1f}秒 ({st})",
                         font=self.font_small, bg=CARD_BG, fg=TEXT, anchor="w").pack(anchor="w")

        # ── 答題明細（按題號排序 + 精簡表格）──
        sorted_results = sorted(results, key=lambda r: r["id"])

        dh = tk.Frame(scroll_frame, bg=BG)
        dh.pack(fill="x", pady=(8, 4))
        tk.Label(dh, text="答題明細", font=self.font_heading, bg=BG, fg=TEXT).pack(side="left")
        wrong_cnt = sum(1 for r in results if not r["is_correct"])
        marked_cnt = sum(1 for r in results if r["id"] in self.marked)
        ff = tk.Frame(dh, bg=BG)
        ff.pack(side="right")
        self._detail_rows: list[tuple[tk.Frame, tk.Frame | None, dict]] = []
        for fn, fl in [("all", f"全部 ({total_q})"), ("wrong", f"錯題 ({wrong_cnt})"), ("marked", f"標記 ({marked_cnt})")]:
            b = self._make_btn(ff, fl, lambda f=fn: self._refilter_details(f, ff),
                               bg=PRIMARY if fn == "all" else BTN_FACE,
                               fg="white" if fn == "all" else TEXT,
                               padx=6, pady=2)
            b.pack(side="left", padx=2)

        # 表頭
        self._detail_container = tk.Frame(scroll_frame, bg=BG)
        self._detail_container.pack(fill="x")

        # 圖例說明
        legend_f = tk.Frame(self._detail_container, bg=BG, pady=2)
        legend_f.pack(fill="x")
        for color, desc in [
            (CORRECT_BG, "正確"), (WRONG_BG, "錯誤"), (MARKED_COLOR, "左側黃邊 = 作答時標記猶豫"),
        ]:
            lf = tk.Frame(legend_f, bg=BG)
            lf.pack(side="left", padx=(0, 12))
            tk.Label(lf, bg=color, width=2, relief="raised", bd=1).pack(side="left", padx=(0, 3))
            tk.Label(lf, text=desc, font=self.font_small, bg=BG, fg=TEXT_LIGHT).pack(side="left")
        tk.Label(legend_f, text="(錯題/標記題可點擊展開)", font=self.font_small,
                 bg=BG, fg=TEXT_LIGHT).pack(side="right")

        # 表頭
        hdr = tk.Frame(self._detail_container, bg=PRIMARY, padx=4, pady=3)
        hdr.pack(fill="x")
        for col_text, col_w in [("#", 4), ("", 3), ("難度", 5), ("類別", 10),
                                ("你的答案", 20), ("正確答案", 20)]:
            tk.Label(hdr, text=col_text, font=self.font_small, bg=PRIMARY, fg="white",
                     width=col_w, anchor="w").pack(side="left", padx=1)

        # 表格列（每題一個 wrapper 包住 row + expand）
        for r in sorted_results:
            is_correct = r["is_correct"]
            is_marked = r["id"] in self.marked
            row_bg = CORRECT_BG if is_correct else WRONG_BG
            opts = {"a": r["option_a"], "b": r["option_b"], "c": r["option_c"]}
            sel = r["selected"] or ""
            cor = r["correct"]
            sel_t = f"{sel.upper()}. {opts.get(sel, '')}" if sel in opts else "未作答"
            cor_t = f"{cor.upper()}. {opts.get(cor, '')}"

            wrapper = tk.Frame(self._detail_container, bg=BG)
            wrapper.pack(fill="x")

            # 主列：用外框 Frame 實現左側色條
            row_outer = tk.Frame(wrapper, bg=MARKED_COLOR if is_marked else row_bg,
                                 padx=0, pady=0)
            row_outer.pack(fill="x")

            # 標記題左側 4px 黃色邊條
            if is_marked:
                tk.Frame(row_outer, bg=MARKED_COLOR, width=4).pack(side="left", fill="y")

            row = tk.Frame(row_outer, bg=row_bg, padx=4, pady=2)
            row.pack(side="left", fill="both", expand=True)

            cells = [
                (str(r["id"]), 4),
                ("O" if is_correct else "X", 3),
                (r["difficulty"], 5),
                (r.get("category", "")[:8], 10),
                (sel_t[:30], 20),
                (cor_t[:30], 20),
            ]
            for cell_text, cell_w in cells:
                tk.Label(row, text=cell_text, font=self.font_small, bg=row_bg, fg=TEXT,
                         width=cell_w, anchor="w").pack(side="left", padx=1)

            # 展開區（錯題或標記題可展開查看題目與解析）
            expand = None
            has_expand = not is_correct or is_marked
            if has_expand:
                expand = tk.Frame(wrapper, bg=row_bg, padx=20, pady=4)
                q_parts = r["question"].split("\n\n", 1)
                tk.Label(expand, text=q_parts[0], font=self.font_small, bg=row_bg, fg=TEXT,
                         wraplength=700, justify="left", anchor="w").pack(anchor="w")
                if len(q_parts) > 1 and q_parts[1].strip():
                    tk.Label(expand, text=q_parts[1].strip(), font=self.font_code,
                             bg="#1E1E2E", fg="#CDD6F4", padx=6, pady=3,
                             justify="left", anchor="w").pack(anchor="w", fill="x", pady=2)
                if r["explanation"]:
                    tk.Label(expand, text=f"解析: {r['explanation']}", font=self.font_small,
                             bg=row_bg, fg=TEXT_LIGHT, wraplength=700,
                             justify="left", anchor="w").pack(anchor="w", pady=(2, 0))
                # 標記題額外顯示標記語意
                if is_marked:
                    reason = "錯誤 + 猶豫" if not is_correct else "正確但猶豫"
                    tk.Label(expand, text=f"[標記] 作答時標記此題 — {reason}，建議複習",
                             font=self.font_small, bg=row_bg, fg=WARNING,
                             anchor="w").pack(anchor="w", pady=(3, 0))
                expand.pack_forget()

                def _bind_toggle(widget: tk.Widget, ex: tk.Frame) -> None:
                    widget.bind("<Button-1>", lambda e: self._toggle_expand(ex))
                    widget.config(cursor="hand2")
                _bind_toggle(row_outer, expand)
                _bind_toggle(row, expand)
                for child in row.winfo_children():
                    _bind_toggle(child, expand)

            self._detail_rows.append((wrapper, expand, r))

        bf = tk.Frame(scroll_frame, bg=BG, pady=12)
        bf.pack(fill="x")
        self._make_btn(bf, "返回首頁", self._restart).pack()

    def _toggle_expand(self, expand_frame: tk.Frame) -> None:
        if expand_frame.winfo_manager():
            expand_frame.pack_forget()
        else:
            expand_frame.pack(fill="x")

    def _download_report(self) -> None:
        path = generate_html_report(
            self.name, self.class_name, self.exam_id, self._last_score,
            self._last_results, self._last_summary, self.marked,
        )
        messagebox.showinfo("報告已儲存", f"測驗報告已儲存至：\n{path}")
        webbrowser.open(f"file://{os.path.abspath(path)}")

    def _refilter_details(self, filter_name: str, filter_frame: tk.Frame) -> None:
        for i, child in enumerate(filter_frame.winfo_children()):
            fn = ["all", "wrong", "marked"][i] if i < 3 else "all"
            if fn == filter_name:
                child.config(bg=PRIMARY, fg="white")
            else:
                child.config(bg=BTN_FACE, fg=TEXT)
        for wrapper, expand, r in self._detail_rows:
            show = (filter_name == "all"
                    or (filter_name == "wrong" and not r["is_correct"])
                    or (filter_name == "marked" and r["id"] in self.marked))
            if show:
                wrapper.pack(fill="x")
            else:
                wrapper.pack_forget()
                if expand:
                    expand.pack_forget()

    # ── 工具 ──────────────────────────────────────────
    def _unbind_keys(self) -> None:
        for key in ("<Return>", "<Right>", "<Left>", "<space>", "<BackSpace>",
                    "<Key-a>", "<Key-b>", "<Key-c>", "<Key-A>", "<Key-B>", "<Key-C>"):
            self.unbind_all(key)

    def _clear(self) -> None:
        self._disable_mousewheel()
        self._unbind_keys()
        for w in self.container.winfo_children():
            w.destroy()

    def _restart(self) -> None:
        random.shuffle(self.questions)
        self._show_login()


# ── 入口 ──────────────────────────────────────────────
if __name__ == "__main__":
    app = QuizApp()
    app.mainloop()
