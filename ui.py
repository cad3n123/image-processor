from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QToolButton, QStyle, QDialog, QVBoxLayout, 
    QDialogButtonBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor

class CheckerLabel(QLabel):
    """
    Custom Label that draws a checkerboard background and scales the image 
    to fit the available space without forcing the window to expand.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # IGNORED policy tells the layout: "I don't need a specific size, just give me what you have."
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.current_image = None 

    def set_image(self, pil_img):
        """Converts PIL image to QImage and stores it for painting."""
        if not pil_img:
            self.current_image = None
        else:
            if pil_img.mode != "RGBA":
                pil_img = pil_img.convert("RGBA")
            data = pil_img.tobytes("raw", "RGBA")
            # Create a copy so we own the data (prevents garbage collection issues)
            qim = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
            self.current_image = qim.copy()
        
        self.update() # Trigger a repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 1. Draw Checkerboard Background
        size = 20
        c1 = QColor(60, 60, 60)
        c2 = QColor(40, 40, 40)
        
        # Optimize drawing: only draw within the clip region if possible, 
        # but for simple checkers, looping whole widget is fine for now.
        for y in range(0, self.height(), size):
            for x in range(0, self.width(), size):
                color = c1 if ((x // size) + (y // size)) % 2 == 0 else c2
                painter.fillRect(x, y, size, size, color)
        
        # 2. Draw the Image (Centered & Scaled)
        if self.current_image and not self.current_image.isNull():
            # Calculate aspect-ratio scaled rect
            target_rect = QRect(0, 0, self.width(), self.height())
            scaled_img = self.current_image.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Center the image
            x = (self.width() - scaled_img.width()) // 2
            y = (self.height() - scaled_img.height()) // 2
            
            painter.drawImage(x, y, scaled_img)
            
        painter.end()

class LayerWidget(QWidget):
    """Custom list item widget with visibility and move controls."""
    def __init__(self, item, callback):
        super().__init__()
        self.item = item
        self.callback = callback
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        
        # Visibility Button
        self.vis_btn = QToolButton()
        self.vis_btn.setText("👁")
        self.vis_btn.setCheckable(True)
        self.vis_btn.setChecked(True)
        self.vis_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vis_btn.clicked.connect(lambda c: (self.style_vis(c), callback('vis', item)))
        self.style_vis(True)
        
        # Label
        self.lbl = QLabel(item.data(Qt.ItemDataRole.UserRole).name)
        
        # Move Buttons
        up = QToolButton()
        up.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        up.clicked.connect(lambda: callback('up', item))
        
        down = QToolButton()
        down.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        down.clicked.connect(lambda: callback('down', item))
        
        layout.addWidget(self.vis_btn)
        layout.addWidget(self.lbl)
        layout.addStretch(1)
        layout.addWidget(up)
        layout.addWidget(down)

    def style_vis(self, visible): 
        color = '#4CAF50' if visible else '#666'
        self.vis_btn.setStyleSheet(f"color: {color}; border: none; font-size: 14px;")

class CompareDialog(QDialog):
    """Side-by-side comparison dialog."""
    def __init__(self, parent, before, after):
        super().__init__(parent)
        self.setWindowTitle("Confirm Changes")
        self.resize(800, 500)
        
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        
        for img, txt in [(before, "Before"), (after, "After")]:
            v_box = QVBoxLayout()
            # Reuse our smart CheckerLabel here too so previews don't break the dialog
            lbl = CheckerLabel()
            lbl.setStyleSheet("border: 1px solid #555;")
            lbl.set_image(img)
            
            v_box.addWidget(QLabel(txt, alignment=Qt.AlignmentFlag.AlignCenter))
            v_box.addWidget(lbl)
            row.addLayout(v_box)
            
        layout.addLayout(row)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)