"""Python 資料分析能力評量 — Tkinter 離線版。

啟動方式：
    python quiz_tk.py

需求：Python 3.10+（僅使用標準庫，不需安裝任何套件）。
"""
from __future__ import annotations

import csv
import json
import os
import random
import time
import tkinter as tk
from datetime import datetime
from tkinter import font as tkfont
from tkinter import messagebox, ttk
from typing import Any

# ── 常數 ──────────────────────────────────────────────
QUIZ_CSV = os.path.join(os.path.dirname(__file__), "quiz.csv")
RESULT_CSV = os.path.join(os.path.dirname(__file__), "result_log.csv")
CONFIG_JSON = os.path.join(os.path.dirname(__file__), "class_config.json")
EXAM_DURATION_SEC = 15 * 60  # 15 分鐘
DIFFICULTY_WEIGHT = {"簡單": 1, "中等": 2, "困難": 3}

# ── 色彩 ──────────────────────────────────────────────
BG = "#F5F7FA"
CARD_BG = "#FFFFFF"
PRIMARY = "#1E88E5"
SUCCESS = "#43A047"
DANGER = "#E53935"
WARNING = "#FB8C00"
TEXT = "#212121"
TEXT_LIGHT = "#757575"
CORRECT_BG = "#E8F5E9"
WRONG_BG = "#FFEBEE"


# ── 讀取題庫 ──────────────────────────────────────────
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
        correct = q["answer"].strip().lower()
        is_correct = selected.strip().lower() == correct if selected else False

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
                "explanation": q.get("explanation", ""),
                "knowledge_point": q.get("knowledge_point", ""),
                "chapter": q.get("chapter", ""),
                "q_score": q_score,
            }
        )

    return round(score, 1), results, diff_stats


# ── 儲存結果 ──────────────────────────────────────────
def save_result(
    name: str,
    class_name: str,
    score: float,
    responses: dict[int, str],
    total_q: int,
) -> None:
    row: dict[str, Any] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": name,
        "class": class_name,
        "score": score,
        "total": 100,
        "correct_rate": round(score, 2),
    }
    for i in range(1, total_q + 1):
        row[f"q{i}"] = responses.get(i, "")

    file_exists = os.path.isfile(RESULT_CSV)
    with open(RESULT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys(), quoting=csv.QUOTE_ALL)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# ══════════════════════════════════════════════════════
#  GUI
# ══════════════════════════════════════════════════════
class QuizApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Python 資料分析能力評量")
        self.geometry("900x680")
        self.configure(bg=BG)
        self.resizable(True, True)

        # 字型
        self.font_title = tkfont.Font(family="PingFang TC", size=20, weight="bold")
        self.font_heading = tkfont.Font(family="PingFang TC", size=14, weight="bold")
        self.font_body = tkfont.Font(family="PingFang TC", size=12)
        self.font_small = tkfont.Font(family="PingFang TC", size=10)
        self.font_code = tkfont.Font(family="Menlo", size=11)
        self.font_btn = tkfont.Font(family="PingFang TC", size=12, weight="bold")

        # 資料
        self.questions = load_questions()
        random.shuffle(self.questions)
        self.responses: dict[int, str] = {}
        self.name = ""
        self.class_name = ""
        self.start_time = 0.0
        self.timer_id: str | None = None

        # 容器
        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)

        self._show_login()

    # ── 登入畫面 ──────────────────────────────────────
    def _show_login(self) -> None:
        self._clear()
        frame = tk.Frame(self.container, bg=BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            frame, text="📚 Python 資料分析能力評量", font=self.font_title,
            bg=BG, fg=PRIMARY,
        ).pack(pady=(0, 30))

        card = tk.Frame(frame, bg=CARD_BG, padx=40, pady=30,
                        highlightbackground="#E0E0E0", highlightthickness=1)
        card.pack()

        tk.Label(card, text="👤 考生資訊", font=self.font_heading,
                 bg=CARD_BG, fg=TEXT).grid(row=0, column=0, columnspan=2, pady=(0, 15))

        tk.Label(card, text="姓名", font=self.font_body, bg=CARD_BG, fg=TEXT
                 ).grid(row=1, column=0, sticky="e", padx=(0, 10), pady=5)
        self.entry_name = tk.Entry(card, font=self.font_body, width=20)
        self.entry_name.grid(row=1, column=1, pady=5)

        tk.Label(card, text="班級", font=self.font_body, bg=CARD_BG, fg=TEXT
                 ).grid(row=2, column=0, sticky="e", padx=(0, 10), pady=5)
        self.entry_class = tk.Entry(card, font=self.font_body, width=20)
        self.entry_class.grid(row=2, column=1, pady=5)

        btn = tk.Button(
            card, text="開始測驗", font=self.font_btn,
            bg=PRIMARY, fg="white", activebackground="#1565C0",
            relief="flat", padx=20, pady=8, cursor="hand2",
            command=self._start_quiz,
        )
        btn.grid(row=3, column=0, columnspan=2, pady=(20, 0))

        # 說明
        info = tk.Label(
            frame,
            text="⏱ 測驗時間 15 分鐘 ∣ 📝 100 題選擇題 ∣ 🔒 離線作答",
            font=self.font_small, bg=BG, fg=TEXT_LIGHT,
        )
        info.pack(pady=(20, 0))

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
        self.responses = {}
        self.start_time = time.time()
        self.current_q = 0
        self._show_quiz()

    # ── 測驗畫面 ──────────────────────────────────────
    def _show_quiz(self) -> None:
        self._clear()

        # 頂部列：進度 + 計時
        top = tk.Frame(self.container, bg=CARD_BG, padx=15, pady=8,
                       highlightbackground="#E0E0E0", highlightthickness=1)
        top.pack(fill="x", padx=10, pady=(10, 5))

        self.lbl_progress = tk.Label(top, font=self.font_body, bg=CARD_BG, fg=TEXT)
        self.lbl_progress.pack(side="left")

        self.lbl_timer = tk.Label(top, font=self.font_heading, bg=CARD_BG, fg=DANGER)
        self.lbl_timer.pack(side="right")

        # 題目快速跳轉列
        nav_outer = tk.Frame(self.container, bg=BG)
        nav_outer.pack(fill="x", padx=10, pady=2)
        self.nav_canvas = tk.Canvas(nav_outer, bg=BG, height=32, highlightthickness=0)
        self.nav_canvas.pack(fill="x")
        self.nav_frame = tk.Frame(self.nav_canvas, bg=BG)
        self.nav_canvas.create_window((0, 0), window=self.nav_frame, anchor="nw")
        self.nav_btns: list[tk.Button] = []
        for i in range(len(self.questions)):
            b = tk.Button(
                self.nav_frame, text=str(i + 1), width=3,
                font=self.font_small, relief="flat", bg="#E0E0E0",
                command=lambda idx=i: self._goto_question(idx),
            )
            b.pack(side="left", padx=1)
            self.nav_btns.append(b)

        # 題目區（可滾動）
        mid = tk.Frame(self.container, bg=BG)
        mid.pack(fill="both", expand=True, padx=10, pady=5)

        self.q_card = tk.Frame(mid, bg=CARD_BG, padx=25, pady=20,
                               highlightbackground="#E0E0E0", highlightthickness=1)
        self.q_card.pack(fill="both", expand=True)

        self.lbl_diff = tk.Label(self.q_card, font=self.font_small, bg=CARD_BG)
        self.lbl_diff.pack(anchor="w")

        self.lbl_question = tk.Label(
            self.q_card, font=self.font_body, bg=CARD_BG, fg=TEXT,
            wraplength=780, justify="left", anchor="w",
        )
        self.lbl_question.pack(anchor="w", pady=(10, 5))

        # 程式碼區（有些題目含 code）
        self.txt_code = tk.Text(
            self.q_card, font=self.font_code, bg="#2D2D2D", fg="#D4D4D4",
            height=4, wrap="word", padx=10, pady=8, relief="flat",
        )

        self.selected_var = tk.StringVar(value="")
        self.radio_frame = tk.Frame(self.q_card, bg=CARD_BG)
        self.radio_frame.pack(anchor="w", pady=(10, 0), fill="x")

        self.radios: list[tk.Radiobutton] = []
        for opt in ("a", "b", "c"):
            rb = tk.Radiobutton(
                self.radio_frame, variable=self.selected_var, value=opt,
                font=self.font_body, bg=CARD_BG, fg=TEXT,
                activebackground=CARD_BG, selectcolor=CARD_BG,
                anchor="w", wraplength=740, justify="left",
                command=self._on_select,
            )
            rb.pack(anchor="w", pady=3, fill="x")
            self.radios.append(rb)

        # 底部導覽列
        bot = tk.Frame(self.container, bg=BG, pady=8)
        bot.pack(fill="x", padx=10)

        self.btn_prev = tk.Button(
            bot, text="◀ 上一題", font=self.font_btn,
            bg="#78909C", fg="white", relief="flat", padx=15, pady=6,
            command=self._prev_q,
        )
        self.btn_prev.pack(side="left")

        self.btn_submit = tk.Button(
            bot, text="交卷", font=self.font_btn,
            bg=DANGER, fg="white", relief="flat", padx=15, pady=6,
            command=self._confirm_submit,
        )
        self.btn_submit.pack(side="left", padx=20)

        self.btn_next = tk.Button(
            bot, text="下一題 ▶", font=self.font_btn,
            bg=PRIMARY, fg="white", relief="flat", padx=15, pady=6,
            command=self._next_q,
        )
        self.btn_next.pack(side="right")

        self._render_question()
        self._tick()

    # ── 題目渲染 ──────────────────────────────────────
    def _render_question(self) -> None:
        q = self.questions[self.current_q]
        qid = int(q["id"])
        total = len(self.questions)
        idx = self.current_q

        # 進度
        answered = sum(1 for i in range(total) if int(self.questions[i]["id"]) in self.responses)
        self.lbl_progress.config(
            text=f"第 {idx + 1}/{total} 題（已作答 {answered} 題）"
        )

        # 難度標籤
        diff = q["difficulty"]
        diff_colors = {"簡單": SUCCESS, "中等": WARNING, "困難": DANGER}
        self.lbl_diff.config(
            text=f"【{diff}】{q.get('category', '')}",
            fg=diff_colors.get(diff, TEXT_LIGHT),
        )

        # 題目文字：分離程式碼區塊
        parts = q["question"].split("\n\n", 1)
        self.lbl_question.config(text=parts[0])

        self.txt_code.pack_forget()
        if len(parts) > 1 and parts[1].strip():
            self.txt_code.pack(anchor="w", pady=(5, 5), fill="x")
            self.txt_code.config(state="normal")
            self.txt_code.delete("1.0", "end")
            self.txt_code.insert("1.0", parts[1].strip())
            self.txt_code.config(state="disabled", height=min(8, parts[1].count("\n") + 2))

        # 選項
        labels = {"a": q["option_a"], "b": q["option_b"], "c": q["option_c"]}
        for rb, opt in zip(self.radios, ("a", "b", "c")):
            rb.config(text=f"  {opt.upper()}. {labels[opt]}")

        # 回復已選答案
        prev = self.responses.get(qid, "")
        self.selected_var.set(prev)

        # 導覽列高亮
        for i, btn in enumerate(self.nav_btns):
            bid = int(self.questions[i]["id"])
            if i == idx:
                btn.config(bg=PRIMARY, fg="white")
            elif bid in self.responses:
                btn.config(bg=SUCCESS, fg="white")
            else:
                btn.config(bg="#E0E0E0", fg=TEXT)

        # 上一題 / 下一題按鈕狀態
        self.btn_prev.config(state="normal" if idx > 0 else "disabled")
        self.btn_next.config(state="normal" if idx < total - 1 else "disabled")

    def _on_select(self) -> None:
        qid = int(self.questions[self.current_q]["id"])
        self.responses[qid] = self.selected_var.get()
        # 更新導覽列
        btn = self.nav_btns[self.current_q]
        if self.current_q != self.current_q:  # won't trigger; keep nav highlight
            pass
        btn.config(bg=PRIMARY, fg="white")

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
        val = self.selected_var.get()
        if val:
            qid = int(self.questions[self.current_q]["id"])
            self.responses[qid] = val

    # ── 計時器 ────────────────────────────────────────
    def _tick(self) -> None:
        elapsed = time.time() - self.start_time
        remaining = max(0, EXAM_DURATION_SEC - int(elapsed))
        mins, secs = divmod(remaining, 60)
        self.lbl_timer.config(text=f"⏱ {mins:02d}:{secs:02d}")
        if remaining <= 60:
            self.lbl_timer.config(fg=DANGER)
        if remaining <= 0:
            self._submit()
            return
        self.timer_id = self.after(1000, self._tick)

    # ── 交卷 ──────────────────────────────────────────
    def _confirm_submit(self) -> None:
        unanswered = sum(
            1 for q in self.questions if int(q["id"]) not in self.responses
        )
        msg = f"確定要交卷嗎？"
        if unanswered > 0:
            msg += f"\n\n⚠️ 還有 {unanswered} 題未作答！"
        if messagebox.askyesno("確認交卷", msg):
            self._submit()

    def _submit(self) -> None:
        self._save_current()
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None

        score, results, diff_stats = evaluate(self.questions, self.responses)
        save_result(self.name, self.class_name, score, self.responses, len(self.questions))
        self._show_results(score, results, diff_stats)

    # ── 結果畫面 ──────────────────────────────────────
    def _show_results(
        self, score: float, results: list[dict], diff_stats: dict
    ) -> None:
        self._clear()

        # 可滾動容器
        canvas = tk.Canvas(self.container, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG)

        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # macOS 滾輪支援
        def _on_mousewheel(event: Any) -> None:
            canvas.yview_scroll(-1 * event.delta, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # ── 成績卡 ──
        total_correct = sum(1 for r in results if r["is_correct"])
        total_q = len(results)
        rate = (score / 100) * 100

        header = tk.Frame(scroll_frame, bg=CARD_BG, padx=20, pady=15,
                          highlightbackground="#E0E0E0", highlightthickness=1)
        header.pack(fill="x", pady=(0, 10))

        color = SUCCESS if score >= 60 else DANGER
        emoji = self._get_emoji(rate)
        tk.Label(
            header, text=f"{emoji} {self.name}（{self.class_name}）",
            font=self.font_heading, bg=CARD_BG, fg=TEXT,
        ).pack(anchor="w")

        score_frame = tk.Frame(header, bg=CARD_BG)
        score_frame.pack(fill="x", pady=(10, 0))

        for label, value, c in [
            ("總分", f"{score}/100", color),
            ("答對", f"{total_correct}/{total_q}", TEXT),
            ("及格", "通過 ✓" if score >= 60 else "未通過 ✗", color),
        ]:
            box = tk.Frame(score_frame, bg=CARD_BG)
            box.pack(side="left", expand=True)
            tk.Label(box, text=label, font=self.font_small, bg=CARD_BG, fg=TEXT_LIGHT).pack()
            tk.Label(box, text=value, font=self.font_heading, bg=CARD_BG, fg=c).pack()

        # 各難度統計
        diff_frame = tk.Frame(scroll_frame, bg=CARD_BG, padx=20, pady=12,
                              highlightbackground="#E0E0E0", highlightthickness=1)
        diff_frame.pack(fill="x", pady=(0, 10))
        tk.Label(diff_frame, text="各難度得分", font=self.font_heading,
                 bg=CARD_BG, fg=TEXT).pack(anchor="w", pady=(0, 8))

        for diff_name in ("簡單", "中等", "困難"):
            if diff_name not in diff_stats:
                continue
            ds = diff_stats[diff_name]
            rate_d = (ds["correct"] / ds["count"] * 100) if ds["count"] else 0
            row = tk.Frame(diff_frame, bg=CARD_BG)
            row.pack(fill="x", pady=2)
            diff_colors = {"簡單": SUCCESS, "中等": WARNING, "困難": DANGER}
            tk.Label(
                row, text=f"【{diff_name}】", font=self.font_body,
                bg=CARD_BG, fg=diff_colors.get(diff_name, TEXT), width=6,
            ).pack(side="left")
            tk.Label(
                row,
                text=f"{ds['correct']}/{ds['count']} 題　{round(ds['points'], 1)}/{round(ds['max'], 1)} 分　正確率 {rate_d:.0f}%",
                font=self.font_body, bg=CARD_BG, fg=TEXT,
            ).pack(side="left", padx=10)

        # ── 答題詳情 ──
        detail_lbl = tk.Label(
            scroll_frame, text="📋 答題詳情", font=self.font_heading, bg=BG, fg=TEXT,
        )
        detail_lbl.pack(anchor="w", pady=(10, 5))

        for r in results:
            bg = CORRECT_BG if r["is_correct"] else WRONG_BG
            card = tk.Frame(scroll_frame, bg=bg, padx=15, pady=10,
                            highlightbackground="#E0E0E0", highlightthickness=1)
            card.pack(fill="x", pady=2)

            status = "✅" if r["is_correct"] else "❌"
            q_parts = r["question"].split("\n\n", 1)
            tk.Label(
                card,
                text=f'{status} 第 {r["id"]} 題 【{r["difficulty"]}】 {q_parts[0]}',
                font=self.font_body, bg=bg, fg=TEXT,
                wraplength=780, justify="left", anchor="w",
            ).pack(anchor="w")

            if len(q_parts) > 1 and q_parts[1].strip():
                code_lbl = tk.Label(
                    card, text=q_parts[1].strip(), font=self.font_code,
                    bg="#2D2D2D", fg="#D4D4D4", padx=8, pady=4,
                    justify="left", anchor="w",
                )
                code_lbl.pack(anchor="w", pady=(4, 4), fill="x")

            opts = {"a": r["option_a"], "b": r["option_b"], "c": r["option_c"]}
            sel = r["selected"] or "未作答"
            cor = r["correct"]
            sel_text = f"{sel.upper()}. {opts.get(sel, '')}" if sel in opts else sel
            cor_text = f"{cor.upper()}. {opts.get(cor, '')}"

            tk.Label(
                card,
                text=f"你的答案: {sel_text}　｜　正確答案: {cor_text}",
                font=self.font_small, bg=bg, fg=TEXT_LIGHT,
                justify="left", anchor="w",
            ).pack(anchor="w", pady=(4, 0))

            if r["explanation"]:
                tk.Label(
                    card,
                    text=f"💡 {r['explanation']}",
                    font=self.font_small, bg=bg, fg=TEXT_LIGHT,
                    wraplength=780, justify="left", anchor="w",
                ).pack(anchor="w", pady=(2, 0))

        # 底部：重新測驗按鈕
        btn_frame = tk.Frame(scroll_frame, bg=BG, pady=15)
        btn_frame.pack(fill="x")
        tk.Button(
            btn_frame, text="🔄 重新測驗", font=self.font_btn,
            bg=PRIMARY, fg="white", relief="flat", padx=20, pady=8,
            command=self._restart,
        ).pack()

    # ── 工具 ──────────────────────────────────────────
    def _clear(self) -> None:
        for w in self.container.winfo_children():
            w.destroy()

    def _restart(self) -> None:
        random.shuffle(self.questions)
        self._show_login()

    @staticmethod
    def _get_emoji(rate: float) -> str:
        if rate >= 90:
            return "🏆"
        if rate >= 80:
            return "🥇"
        if rate >= 70:
            return "👏"
        if rate >= 60:
            return "💡"
        return "💪"


# ── 入口 ──────────────────────────────────────────────
if __name__ == "__main__":
    app = QuizApp()
    app.mainloop()
