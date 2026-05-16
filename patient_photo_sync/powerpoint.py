"""PowerPoint COM integration."""

from __future__ import annotations

import importlib.util

if importlib.util.find_spec("win32com") is not None:
    import win32com.client
else:  # pragma: no cover - Linux/CI or machines without pywin32
    win32com = None


class PowerPointClient:
    """Paste the clipboard image into the active PowerPoint slide."""

    def __init__(self, target_top: int, target_height: int, slide_width: int, max_width: int) -> None:
        self.target_top = target_top
        self.target_height = target_height
        self.slide_width = slide_width
        self.max_width = max_width

    def paste_clipboard_image(self, caption: str) -> None:
        """Set the first shape text, paste clipboard image, resize, and add a new slide."""

        if win32com is None:
            raise RuntimeError("pywin32 is required for PowerPoint automation on Windows.")

        ppt_app = win32com.client.GetActiveObject("PowerPoint.Application")
        ppt_app.ActiveWindow.Activate()
        active_slide = ppt_app.ActiveWindow.View.Slide

        if active_slide.Shapes.Count >= 1:
            active_slide.Shapes(1).TextFrame.TextRange.Text = caption

        pasted_range = active_slide.Shapes.Paste()
        pasted_shape = pasted_range.Item(1) if hasattr(pasted_range, "Item") else pasted_range
        pasted_shape.LockAspectRatio = 1
        pasted_shape.Height = self.target_height

        if pasted_shape.Width > self.max_width:
            pasted_shape.Width = self.max_width

        pasted_shape.Left = (self.slide_width - pasted_shape.Width) / 2
        pasted_shape.Top = self.target_top
        ppt_app.ActivePresentation.Slides.Add(active_slide.SlideIndex + 1, active_slide.Layout).Select()
