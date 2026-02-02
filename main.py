import sys
import os
from PIL import Image
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QPushButton, QFileDialog, QMessageBox, QSplitter, 
    QFrame, QAbstractItemView, QInputDialog, QListWidgetItem, QProgressDialog,
    QLabel, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon

#  Import our custom modules
from ui import LayerWidget, CheckerLabel, CompareDialog
from logic import (
    Layer, Worker, to_alpha, invert_color, composite_layers, remove, 
    load_pdf_layers, save_layers_to_pdf
)

class EditorBase(QWidget):
    """
    Base class containing the List + Preview UI pattern.
    Subclasses define specific buttons and processing logic.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        root = QHBoxLayout(self)
        
        # Left Panel (Controls)
        left_layout = QVBoxLayout()
        self.btns_top = QHBoxLayout()
        left_layout.addLayout(self.btns_top)
        
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.itemClicked.connect(self.refresh)
        self.list.itemDoubleClicked.connect(self.rename)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        left_layout.addWidget(self.list)

        # Placeholder for specific controls (Effects, etc)
        self.controls_layout = QVBoxLayout()
        left_layout.addLayout(self.controls_layout)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(line)
        
        # Bottom Actions
        self.btns_bottom = QHBoxLayout()
        left_layout.addLayout(self.btns_bottom)

        # Right Panel (Preview)
        self.preview = CheckerLabel()
        self.preview.setStyleSheet("border: 2px solid #333;")
        
        # Splitter
        container = QWidget()
        container.setLayout(left_layout)
        
        split = QSplitter()
        split.addWidget(container)
        split.addWidget(self.preview)
        split.setSizes([300, 800])
        
        root.addWidget(split)

    def add_btn(self, txt, func, layout, bg=None):
        b = QPushButton(txt)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(func)
        if bg:
            b.setStyleSheet(f"background-color: {bg}; font-weight: bold;")
        layout.addWidget(b)

    def get_node(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None
    
    def get_all_nodes(self):
        return [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())]

    def add_layer_to_list(self, layer):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, layer)
        self.list.addItem(item)
        widget = LayerWidget(item, self.handle_list_action)
        item.setSizeHint(widget.sizeHint())
        self.list.setItemWidget(item, widget)

    def handle_list_action(self, action, item):
        row = self.list.row(item)
        node = item.data(Qt.ItemDataRole.UserRole)
        
        if action == 'vis':
            node.visible = not node.visible
        elif action == 'up' and row > 0:
            self.list.takeItem(row)
            self.list.insertItem(row - 1, item)
            self.list.setItemWidget(item, LayerWidget(item, self.handle_list_action))
            self.list.setCurrentRow(row - 1)
        elif action == 'down' and row < self.list.count() - 1:
            self.list.takeItem(row)
            self.list.insertItem(row + 1, item)
            self.list.setItemWidget(item, LayerWidget(item, self.handle_list_action))
            self.list.setCurrentRow(row + 1)
        
        self.refresh()

    def del_img(self):
        row = self.list.currentRow()
        if row >= 0:
            self.list.takeItem(row)
            self.refresh()

    def rename(self, item):
        node = item.data(Qt.ItemDataRole.UserRole)
        name, ok = QInputDialog.getText(self, "Rename", "Name:", text=node.name)
        if ok and name:
            node.name = name
            self.list.setItemWidget(item, LayerWidget(item, self.handle_list_action))

    def refresh(self):
        # To be implemented by subclasses
        pass

class ImageEditor(EditorBase):
    def __init__(self):
        super().__init__()
        # Top Buttons
        self.add_btn("Import Images", self.load_img, self.btns_top)
        self.add_btn("Remove", self.del_img, self.btns_top)
        
        # Effect Controls
        self.controls_layout.addWidget(QLabel("Effects:", styleSheet="font-weight:bold; margin-top:10px"))
        self.add_btn("Greyscale -> Alpha", lambda: self.apply(to_alpha), self.controls_layout)
        self.add_btn("Invert Colors", lambda: self.apply(invert_color), self.controls_layout)
        self.add_btn("Remove Background", self.bg_remove_flow, self.controls_layout)
        
        # Bottom Buttons
        self.add_btn("View Composite", self.show_composite, self.btns_bottom)
        self.add_btn("Export Composite", self.export, self.btns_bottom, "#2a82da")
        
        self.comp_img = None

    def load_img(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Import", "", "Images (*.png *.jpg *.jpeg)")
        for p in paths:
            try:
                self.add_layer_to_list(Layer(os.path.basename(p), Image.open(p)))
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def apply(self, func):
        node = self.get_node()
        if node:
            node.img = func(node.img)
            self.refresh()

    def bg_remove_flow(self):
        node = self.get_node()
        if not node: return
        
        pd = QProgressDialog("Processing...", None, 0, 0, self)
        pd.show()
        
        self.worker = Worker(remove, node.img)
        self.worker.finished.connect(lambda res: (pd.close(), self.confirm_bg(node, res)))
        self.worker.error.connect(lambda e: (pd.close(), QMessageBox.critical(self, "Error", e)))
        self.worker.start()

    def confirm_bg(self, node, new_img):
        if CompareDialog(self, node.img, new_img).exec():
            node.img = new_img
            self.refresh()

    def show_composite(self):
        layers = self.get_all_nodes()
        self.comp_img = composite_layers(layers)
        self.preview.set_image(self.comp_img)
        self.list.clearSelection()

    def refresh(self):
        if self.list.selectedItems():
            self.preview.set_image(self.get_node().display)
        else:
            self.show_composite()

    def export(self):
        img = self.comp_img
        if self.list.selectedItems():
            img = self.get_node().display
        if not img: return
            
        path, _ = QFileDialog.getSaveFileName(self, "Save", "composite.png", "*.png")
        if path:
            img.save(path)

class PdfEditor(EditorBase):
    def __init__(self):
        super().__init__()
        # Top Buttons
        self.add_btn("Import PDF", self.load_pdf, self.btns_top)
        self.add_btn("Remove Page", self.del_img, self.btns_top)
        
        # Bottom Buttons
        self.controls_layout.addStretch() # Push export to bottom
        self.add_btn("Export Combined PDF", self.export, self.btns_bottom, "#2a82da")

    def load_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import PDF", "", "PDF Files (*.pdf)")
        if not path: return
        
        try:
            layers = load_pdf_layers(path)
            for l in layers:
                self.add_layer_to_list(l)
        except Exception as e:
            QMessageBox.critical(self, "Error importing PDF", str(e))

    def refresh(self):
        # For PDF, we just show the selected page. There is no 'composite' view.
        node = self.get_node()
        if node:
            self.preview.set_image(node.display)
        else:
            self.preview.set_image(None)

    def export(self):
        layers = self.get_all_nodes()
        if not layers: return
        
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "combined.pdf", "*.pdf")
        if path:
            try:
                save_layers_to_pdf(layers, path)
                QMessageBox.information(self, "Success", "PDF Saved Successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error Saving", str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pro Media Studio")
        self.resize(1100, 750)
        self.setStyle()
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.tabs.addTab(ImageEditor(), "Image Compositor")
        self.tabs.addTab(PdfEditor(), "PDF Tools")

    def setStyle(self):
        QApplication.setStyle("Fusion")
        p = self.palette()
        p.setColor(p.ColorRole.Window, QColor(53, 53, 53))
        p.setColor(p.ColorRole.WindowText, Qt.GlobalColor.white)
        p.setColor(p.ColorRole.Base, QColor(35, 35, 35))
        p.setColor(p.ColorRole.Text, Qt.GlobalColor.white)
        p.setColor(p.ColorRole.Button, QColor(53, 53, 53))
        p.setColor(p.ColorRole.ButtonText, Qt.GlobalColor.white)
        self.setPalette(p)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())