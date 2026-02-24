import sys
from PyQt6.QtWidgets import QApplication, QFileDialog, QAbstractItemView

class OrderedFileDialog(QFileDialog):
    def __init__(self):
        super().__init__()
        self.setFileMode(QFileDialog.FileMode.ExistingFiles)
        self.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        self._ordered = []
        self._views_connected = set()
        
    def showEvent(self, event):
        super().showEvent(event)
        self.connect_views()
        
    def connect_views(self):
        for view in self.findChildren(QAbstractItemView):
            sel_model = view.selectionModel()
            if sel_model and id(sel_model) not in self._views_connected:
                sel_model.selectionChanged.connect(self._on_selection_changed)
                self._views_connected.add(id(sel_model))

    def _on_selection_changed(self):
        print("Selection changed!", self.selectedFiles())

app = QApplication(sys.argv)
d = OrderedFileDialog()
d.connect_views()
print(d.findChildren(QAbstractItemView))
