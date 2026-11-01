import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import tempfile

# 尝试导入 mpmath
try:
    from mpmath import mp
except ImportError:
    mp = None


class PiBirthdayFinder:
    def __init__(self, root):
        self.root = root
        self.root.title("圆周率生日查找器")
        self.root.geometry("520x320")
        self.root.resizable(False, False)

        # 状态变量
        self.searching = False
        self.cancel_flag = False

        self._build_ui()

    def _build_ui(self):
        # 标题
        title = tk.Label(self.root, text="🎂 圆周率生日查找器",
                         font=("微软雅黑", 16, "bold"), fg="#2c3e50")
        title.pack(pady=10)

        # 输入区
        frame_input = tk.Frame(self.root)
        frame_input.pack(pady=5)

        tk.Label(frame_input, text="请输入生日 (如 19900101 或 0101):",
                 font=("微软雅黑", 11)).pack(side=tk.LEFT, padx=5)

        self.entry = tk.Entry(frame_input, font=("Consolas", 12), width=18)
        self.entry.pack(side=tk.LEFT, padx=5)
        self.entry.insert(0, "19900101")

        # 精度选择
        frame_precision = tk.Frame(self.root)
        frame_precision.pack(pady=5)
        tk.Label(frame_precision, text="查找范围 (位数):",
                 font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=5)
        self.precision_var = tk.StringVar(value="1000000000")
        precision_combo = ttk.Combobox(
            frame_precision, textvariable=self.precision_var,
            values=["100000", "1000000", "10000000", "100000000", "1000000000"],
            width=15, state="readonly")
        precision_combo.pack(side=tk.LEFT, padx=5)

        # 按钮
        frame_btn = tk.Frame(self.root)
        frame_btn.pack(pady=10)

        self.btn_search = tk.Button(frame_btn, text="开始查找",
                                    font=("微软雅黑", 11, "bold"),
                                    bg="#3498db", fg="white",
                                    width=12, command=self.start_search)
        self.btn_search.pack(side=tk.LEFT, padx=10)

        self.btn_cancel = tk.Button(frame_btn, text="取消",
                                    font=("微软雅黑", 11),
                                    bg="#e74c3c", fg="white",
                                    width=12, state=tk.DISABLED,
                                    command=self.cancel_search)
        self.btn_cancel.pack(side=tk.LEFT, padx=10)

        # 进度条
        self.progress = ttk.Progressbar(self.root, mode="indeterminate",
                                        length=460)
        self.progress.pack(pady=10)

        # 状态标签
        self.status_label = tk.Label(self.root, text="就绪",
                                     font=("微软雅黑", 10), fg="#7f8c8d")
        self.status_label.pack(pady=5)

        # 提示
        tip = tk.Label(self.root,
                       text="提示: 10亿位计算需要较长时间和约 1GB 内存，请耐心等待。",
                       font=("微软雅黑", 9), fg="#95a5a6")
        tip.pack(side=tk.BOTTOM, pady=8)

    # ---------------- 搜索逻辑 ----------------
    def start_search(self):
        if mp is None:
            messagebox.showerror("缺少依赖",
                                 "请先安装 mpmath：\n\npip install mpmath")
            return

        birthday = self.entry.get().strip()
        if not birthday.isdigit():
            messagebox.showwarning("输入错误", "生日必须是纯数字，例如 19900101")
            return
        if len(birthday) < 4:
            messagebox.showwarning("输入错误", "生日至少需要4位数字")
            return

        try:
            precision = int(self.precision_var.get())
        except ValueError:
            messagebox.showwarning("输入错误", "请选择有效的位数范围")
            return

        self.searching = True
        self.cancel_flag = False
        self.btn_search.config(state=tk.DISABLED)
        self.btn_cancel.config(state=tk.NORMAL)
        self.progress.start(10)
        self.status_label.config(text="正在计算圆周率……", fg="#2980b9")

        # 后台线程执行，避免界面卡死
        t = threading.Thread(target=self._do_search,
                             args=(birthday, precision), daemon=True)
        t.start()

    def cancel_search(self):
        self.cancel_flag = True
        self.status_label.config(text="正在取消……", fg="#e67e22")

    def _do_search(self, birthday, precision):
        try:
            # 设置精度（多留一些余量，避免舍入误差）
            mp.dps = precision + 50

            self._update_status(f"正在计算 {precision:,} 位圆周率……")

            # 计算 pi 的字符串（注意：mpmath 的 str(pi) 在小数点后是准确的）
            pi_str = str(mp.pi)

            if self.cancel_flag:
                self._finish_cancel()
                return

            # 去掉 "3." 部分，只保留小数位
            if "." in pi_str:
                int_part, frac_part = pi_str.split(".")
            else:
                frac_part = pi_str

            self._update_status("正在查找生日数字……")

            # 查找（只在前 precision 位中查找）
            search_region = frac_part[:precision]
            idx = search_region.find(birthday)

            if idx == -1:
                # 未找到
                self.root.after(0, lambda: self._show_not_found(precision))
            else:
                # idx 是在 frac_part 中的索引（从0开始）
                # 圆周率小数位第 1 位对应 idx=0
                start_pos = idx + 1  # 第几位（从1开始）
                end_pos = idx + len(birthday)

                # 截取左右各20位（相对于生日数字）
                left_start = max(0, idx - 20)
                right_end = min(len(frac_part), idx + len(birthday) + 20)

                left_part = frac_part[left_start:idx]
                match_part = frac_part[idx:idx + len(birthday)]
                right_part = frac_part[idx + len(birthday):right_end]

                self.root.after(0, lambda: self._show_result(
                    left_part, match_part, right_part,
                    start_pos, end_pos, precision))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(
                "错误", f"发生错误：\n{e}"))
            self._finish_cancel()

    def _update_status(self, text):
        self.root.after(0, lambda: self.status_label.config(
            text=text, fg="#2980b9"))

    def _finish_cancel(self):
        self.searching = False
        self.root.after(0, self._reset_buttons)

    def _reset_buttons(self):
        self.progress.stop()
        self.btn_search.config(state=tk.NORMAL)
        self.btn_cancel.config(state=tk.DISABLED)
        self.status_label.config(text="就绪", fg="#7f8c8d")

    # ---------------- 结果显示 ----------------
    def _show_result(self, left, match, right, start_pos, end_pos, precision):
        self._reset_buttons()

        # 构造带下划线的显示：用 Unicode 组合下划线标记生日数字
        # 这里采用换行 + 分段标注的方式，兼容性更好
        combined = left + match + right

        # 用 Unicode 组合字符 U+0332 (combining low line) 给生日数字加下划线
        underlined_match = "".join(ch + "\u0332" for ch in match)
        display_line = left + underlined_match + right

        result_text = (
            f"🎉 在第 {start_pos:,} 到第 {end_pos:,} 位找到了你的生日！\n\n"
            f"（圆周率小数位，共查找 {precision:,} 位）\n\n"
            f"上下文（生日数字带下划线）：\n"
            f"{display_line}\n\n"
            f"生日数字：{match}\n"
            f"起始位置：第 {start_pos:,} 位\n"
            f"结束位置：第 {end_pos:,} 位\n"
            f"跨度：{end_pos - start_pos + 1} 位"
        )

        # 使用 Toplevel 自定义弹窗，方便显示大段文字
        self._popup("查找结果", result_text, color="#27ae60")

    def _show_not_found(self, precision):
        self._reset_buttons()
        msg = (f"😢 很遗憾，在前 {precision:,} 位圆周率中\n"
               f"没有找到你的生日数字。\n\n"
               f"可以尝试增加查找范围，或换一个生日格式。")
        self._popup("未找到", msg, color="#c0392b")

    def _popup(self, title, text, color="#2c3e50"):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("760x360")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text=title, font=("微软雅黑", 13, "bold"),
                 fg=color).pack(pady=8)

        # 带滚动条的文本框，方便查看长结果
        frame = tk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(frame, wrap=tk.WORD,
                              font=("Consolas", 11),
                              yscrollcommand=scrollbar.set,
                              bg="#fdfdfd")
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)

        text_widget.insert(tk.END, text)
        text_widget.config(state=tk.DISABLED)

        tk.Button(win, text="关闭", font=("微软雅黑", 10),
                  width=10, command=win.destroy).pack(pady=8)


def main():
    if mp is None:
        print("请先安装依赖：pip install mpmath")
        return
    root = tk.Tk()
    app = PiBirthdayFinder(root)
    root.mainloop()


if __name__ == "__main__":
    main()
