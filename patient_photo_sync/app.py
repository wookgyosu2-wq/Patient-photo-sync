"""Tkinter desktop app that ports the original AutoHotkey workflow to Python."""

from __future__ import annotations

from datetime import date
import importlib.util
import re
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from .input_automation import DesktopAutomation
from .ocr_engine import OcrEngine
from .powerpoint import PowerPointClient

if importlib.util.find_spec("keyboard") is not None:
    import keyboard
else:  # pragma: no cover - dependency absence
    keyboard = None


SPECIAL_MODES = {"술 중 구내", "술 중 구외", "술 후 종물"}
BIOPSY_CODES = [
    "PSU20044",
    "PSU20084",
    "PSU20085",
    "PSU20094",
    "C8532",
    "Q2202G",
    "PSU20103",
    "PSU20054",
    "PSU20137",
]

TARGET_TOP = 110
TARGET_HEIGHT = 410
SLIDE_WIDTH = 720
MAX_WIDTH = 680


class PatientPhotoSyncApp:
    """Main GUI and workflow controller."""

    def __init__(self) -> None:
        self.current_mode = ""
        self.selected_step = "초진"
        self.input_date = date.today().strftime("%Y-%m-%d")
        self.is_ready = False
        self.intra_no = 1
        self.temp_target_mode = ""

        self.desktop = DesktopAutomation()
        self.ocr = OcrEngine()
        self.powerpoint = PowerPointClient(TARGET_TOP, TARGET_HEIGHT, SLIDE_WIDTH, MAX_WIDTH)

        self.root = tk.Tk()
        self.root.title("Conf. & 외래 Master - 이정빈 Python v1.0")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)
        self._build_main_gui()
        self._install_hotkeys()

    def run(self) -> None:
        self.root.mainloop()

    def _build_main_gui(self) -> None:
        self._button(self.root, "❓ 사용 설명서 확인", self.show_manual, width=35).pack(padx=10, pady=(10, 8), fill="x")

        photo_frame = ttk.LabelFrame(self.root, text="OP conf. / 외래 사진")
        photo_frame.pack(padx=10, pady=5, fill="x")

        for modality in ["Panorama", "CBCT", "PNS CT", "Neck CT"]:
            self._build_modality_row(photo_frame, modality)

        ttk.Label(photo_frame, text="● EMR / 특수 모드 (F1~F12 / ` 키)").pack(anchor="w", padx=10, pady=(12, 2))
        self._button(photo_frame, "EMR 사진 넣기 (기존 방식)", self.show_emr_sub_gui, width=35).pack(padx=10, pady=2, fill="x")

        special_row = ttk.Frame(photo_frame)
        special_row.pack(padx=10, pady=(2, 10), fill="x")
        for mode in ["술 중 구내", "술 중 구외", "술 후 종물"]:
            self._button(special_row, mode, lambda mode=mode: self.show_special_sub_gui(mode), width=11).pack(side="left", padx=(0, 5))

        biopsy_frame = ttk.LabelFrame(self.root, text="외래1 후잡")
        biopsy_frame.pack(padx=10, pady=(12, 10), fill="x")
        self._button(
            biopsy_frame,
            "바이옵시 확인 (처방코드 자동입력)",
            lambda: self.set_mode("바이옵시 확인"),
            width=35,
        ).pack(padx=10, pady=10, fill="x")

        self.status = ttk.Label(self.root, text="모드를 선택하세요.", foreground="#444")
        self.status.pack(padx=10, pady=(0, 10), fill="x")

        self.root.bind("<Escape>", lambda _event: self.reset_mode())
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def _build_modality_row(self, parent: ttk.Frame, modality: str) -> None:
        ttk.Label(parent, text=f"● {modality}").pack(anchor="w", padx=10, pady=(8, 2))
        row = ttk.Frame(parent)
        row.pack(padx=10, pady=2, fill="x")
        for step in ["초진", "술 전", "술 후"]:
            self._button(row, step, lambda step=step, modality=modality: self.set_mode(f"{step} {modality}"), width=8).pack(side="left", padx=(0, 5))
        self._button(row, "None", lambda modality=modality: self.set_mode(modality), width=8).pack(side="left")

    def _button(self, parent: tk.Misc, text: str, command: Callable[[], None], width: int) -> ttk.Button:
        return ttk.Button(parent, text=text, command=command, width=width)

    def _install_hotkeys(self) -> None:
        for number in range(1, 13):
            self.root.bind(f"<F{number}>", lambda _event, number=number: self.handle_function_key(number))

        self.root.bind("`", lambda _event: self.handle_no_number_key())

        if keyboard is None:
            self._set_status("⚠️ keyboard 패키지가 없어 창이 활성화된 상태에서만 단축키가 동작합니다.")
            return

        for number in range(1, 13):
            keyboard.add_hotkey(f"f{number}", lambda number=number: self._run_on_ui(lambda: self.handle_function_key(number)))
        keyboard.add_hotkey("`", lambda: self._run_on_ui(self.handle_no_number_key))

    def _run_on_ui(self, callback: Callable[[], None]) -> None:
        self.root.after(0, callback)

    def _set_status(self, text: str, clear_after_ms: int | None = None) -> None:
        self.status.configure(text=text)
        if clear_after_ms:
            self.root.after(clear_after_ms, lambda: self.status.configure(text=""))

    def reset_mode(self) -> None:
        self.is_ready = False
        self._set_status("❌ 모드 해제", 1000)

    def set_mode(self, mode_name: str) -> None:
        self.current_mode = mode_name
        self.is_ready = True
        self._set_status(f"✅ [{mode_name}] 활성! 마우스를 대상 위에 올리고 단축키를 누르세요.", 3000)

    def show_special_sub_gui(self, target_name: str) -> None:
        self.temp_target_mode = target_name
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{target_name} 설정")
        dialog.attributes("-topmost", True)
        ttk.Label(dialog, text="촬영 날짜 입력 (YYYY-MM-DD):").pack(padx=10, pady=(10, 2))
        date_var = tk.StringVar(value=self.input_date)
        ttk.Entry(dialog, textvariable=date_var, width=24).pack(padx=10, pady=2)

        def confirm() -> None:
            self.input_date = date_var.get().strip()
            self.current_mode = self.temp_target_mode
            self.is_ready = True
            dialog.destroy()
            self._set_status(f"✅ [{self.current_mode}] 준비 완료! 사진 위에 커서를 두고 단축키를 누르세요.", 3000)

        self._button(dialog, "설정 완료", confirm, width=24).pack(padx=10, pady=10)
        dialog.grab_set()

    def show_emr_sub_gui(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("EMR 옵션 설정")
        dialog.attributes("-topmost", True)
        ttk.Label(dialog, text="진료 단계:").pack(padx=10, pady=(10, 2))
        step_var = tk.StringVar(value=self.selected_step)
        step_box = ttk.Combobox(dialog, textvariable=step_var, values=["초진", "술 전", "술 중", "술 후", "None"], state="readonly", width=22)
        step_box.pack(padx=10, pady=2)
        date_var = tk.StringVar(value=self.input_date)
        ttk.Entry(dialog, textvariable=date_var, width=24).pack(padx=10, pady=2)

        def confirm() -> None:
            self.selected_step = step_var.get()
            self.input_date = date_var.get().strip()
            self.current_mode = "EMR"
            self.is_ready = True
            dialog.destroy()
            self._set_status("✅ EMR 설정 완료!", 2000)

        self._button(dialog, "설정 완료", confirm, width=24).pack(padx=10, pady=10)
        dialog.grab_set()

    def handle_function_key(self, number: int) -> None:
        if not self.is_ready:
            self._set_status("⚠️ 모드를 먼저 선택하세요!", 2000)
            return

        if self.current_mode in SPECIAL_MODES:
            self.intra_no = number
            self._start_background(lambda: self.run_main_logic(use_num=True))
            return

        if number == 1:
            if self.current_mode == "바이옵시 확인":
                self._start_background(self.run_biopsy_logic)
            else:
                self._start_background(lambda: self.run_main_logic(use_num=False))

    def handle_no_number_key(self) -> None:
        if not self.is_ready:
            self._set_status("⚠️ 모드를 먼저 선택하세요!", 2000)
            return
        self._start_background(lambda: self.run_main_logic(use_num=False))

    def _start_background(self, callback: Callable[[], None]) -> None:
        thread = threading.Thread(target=callback, daemon=True)
        thread.start()

    def run_main_logic(self, use_num: bool = False) -> None:
        try:
            mouse_x, mouse_y = self.desktop.mouse_position()
            previous_clipboard = self.desktop.get_clipboard()
            previous_sequence = self.desktop.clipboard_sequence_number()
            self.desktop.clear_clipboard()
            previous_sequence = self.desktop.clipboard_sequence_number() or previous_sequence
            combined_text = ""

            if self.current_mode in SPECIAL_MODES:
                combined_text = self._build_special_caption(use_num)
                self._run_on_ui(lambda: self._set_status("1/4. 대상 창 활성화 중..."))
                time.sleep(0.2)
                self._run_on_ui(lambda: self._set_status("2/4. 사진 꾹 누르는 중..."))
                self.desktop.press_and_release_mouse(mouse_x, mouse_y)
                time.sleep(0.5)
                self._run_on_ui(lambda: self._set_status("3/4. 복사 중 (Ctrl+C)..."))
                self.desktop.copy_hotkey()
                if not self.desktop.wait_clipboard_changed(previous_sequence, timeout_seconds=3):
                    self._run_on_ui(lambda: self._set_status("❌ 복사 실패! 뷰어가 매크로 입력을 막은 것 같습니다.", 3000))
                    return
            else:
                combined_text = self._caption_from_ocr(mouse_x, mouse_y)
                if not combined_text:
                    return
                time.sleep(0.5)
                self.desktop.copy_hotkey()
                if not self.desktop.wait_clipboard_changed(previous_sequence, timeout_seconds=3):
                    self._run_on_ui(lambda: self._set_status("❌ 복사 대기 시간 초과", 2000))
                    return

            self._run_on_ui(lambda: self._set_status("4/4. PPT 전송 중..."))
            try:
                self.powerpoint.paste_clipboard_image(combined_text)
                self._run_on_ui(lambda: self._set_status(f"✨ 완료: {combined_text}", 3000))
            except Exception:
                self._run_on_ui(lambda: self._set_status("⚠️ PPT 연동 실패 (사진은 복사됨)", 3000))
        except Exception:
            self._run_on_ui(lambda: self._set_status("⚠️ 전체 로직 오류 발생", 3000))
        finally:
            if self.desktop.get_clipboard() == "":
                self.desktop.set_clipboard(previous_clipboard)

    def _build_special_caption(self, use_num: bool) -> str:
        if use_num:
            return f"{self.current_mode} ({self.intra_no}) ({self.input_date})"
        return f"{self.current_mode} ({self.input_date})"

    def _caption_from_ocr(self, mouse_x: int, mouse_y: int) -> str:
        self._run_on_ui(lambda: self._set_status("🔍 텍스트 구역 스캔 중..."))
        scan_width = 700 if self.current_mode == "EMR" else 600
        scan_height = 60 if self.current_mode == "EMR" else 300
        ocr_result = self.ocr.read_screen_rect(mouse_x - (scan_width / 2), mouse_y - (scan_height / 2), scan_width, scan_height, "ko")

        if not ocr_result.text:
            self._run_on_ui(lambda: self._set_status("❌ 텍스트 인식 실패", 2000))
            return ""

        if self.current_mode == "EMR":
            prefix = "" if self.selected_step == "None" else f"{self.selected_step} "
            clean_text = re.sub(r"(?i)\.?jpg", "", ocr_result.text)
            clean_text = re.sub(r"\s*\n\s*", " ", clean_text).strip()
            self.desktop.click(mouse_x, mouse_y + 120)
            return f"{prefix}{clean_text} ({self.input_date})"

        match = re.search(r"(\d{4}|\d{2})[-\./\s]\d{1,2}[-\./\s]\d{1,2}", ocr_result.text)
        if not match:
            self._run_on_ui(lambda: self._set_status("❌ 텍스트 인식 실패", 2000))
            return ""

        found_date = re.sub(r"[-\./\s]", "-", match.group(0))
        self.desktop.click(mouse_x, mouse_y)
        return f"{self.current_mode} ({found_date})"

    def run_biopsy_logic(self) -> None:
        old_clipboard = self.desktop.get_clipboard()
        self._run_on_ui(lambda: self._set_status("⚡ 바이옵시 입력 중..."))

        for index, code in enumerate(BIOPSY_CODES, start=1):
            self.desktop.set_clipboard(code)
            time.sleep(0.05)
            self.desktop.paste_hotkey()
            time.sleep(0.25)
            self.desktop.enter()
            time.sleep(0.35)

            if index < len(BIOPSY_CODES):
                self.desktop.enter()
                time.sleep(0.35)
            else:
                self.desktop.type_text("n")
                time.sleep(0.2)

        self.desktop.set_clipboard(old_clipboard)
        self._run_on_ui(lambda: self._set_status("✅ 바이옵시 완료!", 2000))

    def show_manual(self) -> None:
        messagebox.showinfo("사용 설명서", "X-ray: 날짜 위 F1\n특수모드: 사진 위 F1~F12 또는 `")


def main() -> None:
    app = PatientPhotoSyncApp()
    app.run()


if __name__ == "__main__":
    main()
