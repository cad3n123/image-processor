from dataclasses import dataclass
from PIL import Image, ImageOps
import numpy as np
from rembg import remove
from PyQt6.QtCore import QThread, pyqtSignal
import fitz  # PyMuPDF

@dataclass
class Layer:
    name: str
    img: Image.Image
    visible: bool = True

    @property
    def display(self):
        return self.img.convert("RGBA")

class Worker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, func, *args):
        super().__init__()
        self.func = func
        self.args = args

    def run(self):
        try:
            self.finished.emit(self.func(*self.args))
        except Exception as e:
            self.error.emit(str(e))

def to_alpha(img):
    """Converts Greyscale intensity to Alpha transparency."""
    arr = np.array(img.convert('L'))
    h, w = arr.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[..., 3] = 255 - arr
    return Image.fromarray(rgba, 'RGBA')

def invert_color(img):
    """Inverts RGB channels, preserving Alpha."""
    if img.mode != 'RGBA':
        return ImageOps.invert(img.convert('RGB')).convert('RGBA')
    r, g, b, a = img.split()
    return Image.merge('RGBA', (*ImageOps.invert(Image.merge('RGB', (r, g, b))).split(), a))

def composite_layers(layers):
    """Stacks layers bottom-up."""
    if not layers:
        return None
    
    # Calculate max dimensions
    w = max(l.img.width for l in layers)
    h = max(l.img.height for l in layers)
    
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    
    for l in layers:
        if l.visible:
            layer_canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            layer_canvas.paste(l.display, (0, 0))
            canvas = Image.alpha_composite(canvas, layer_canvas)
    return canvas

def load_pdf_layers(path):
    """Opens a PDF and converts all pages to Layer objects."""
    doc = fitz.open(path)
    layers = []
    for i, page in enumerate(doc):
        # Render page to image (dpi=150 is a good balance for screen/edit)
        pix = page.get_pixmap(dpi=150, alpha=True)
        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
        layers.append(Layer(f"Page {i+1}", img))
    return layers

def save_layers_to_pdf(layers, path):
    """Saves a list of layers as a single multi-page PDF."""
    visible_layers = [l.img.convert("RGB") for l in layers if l.visible]
    if not visible_layers:
        return
    
    base = visible_layers[0]
    rest = visible_layers[1:]
    base.save(path, save_all=True, append_images=rest, resolution=150.0)