import io

import barcode
from barcode.writer import SVGWriter


class BaseBarcodeGenerator:
    def generate(self, code):
        raise NotImplementedError("Generators must implement a generate method.")


class Code128Generator(BaseBarcodeGenerator):
    def generate(self, code):
        COD128 = barcode.get_barcode_class("code128")
        writer = SVGWriter()
        code128 = COD128(code, writer=writer)
        buffer = io.BytesIO()
        # Omit human readable text beneath the barcode graphics
        # since label templates render the SKU separately with custom styling
        code128.write(buffer, options={"write_text": False})
        return buffer.getvalue().decode("utf-8")


class EAN13Generator(BaseBarcodeGenerator):
    def generate(self, code):
        # EAN13 requires exactly 12 numeric digits (it calculates the 13th check digit itself)
        digits = "".join(c for c in code if c.isdigit())
        if len(digits) < 12:
            digits = digits.zfill(12)
        else:
            digits = digits[:12]

        EAN = barcode.get_barcode_class("ean13")
        writer = SVGWriter()
        ean = EAN(digits, writer=writer)
        buffer = io.BytesIO()
        ean.write(buffer, options={"write_text": False})
        return buffer.getvalue().decode("utf-8")


class QRGenerator(BaseBarcodeGenerator):
    def generate(self, code):
        # Dynamic server-side fallback placeholder SVG for QR codes
        # QR is mainly rendered via qrious.js in the browser for print outputs
        return '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100" fill="#000"/><text x="50" y="55" fill="#fff" font-size="10" font-family="monospace" text-anchor="middle">QR CODE</text></svg>'


# Factory map
GENERATORS = {
    "CODE128": Code128Generator,
    "EAN13": EAN13Generator,
    "QR": QRGenerator,
}


def generate_barcode_svg(code, barcode_type="CODE128"):
    """
    Looks up the appropriate generator strategy and returns the SVG string.
    Falls back to CODE128 in case of formatting constraints.
    """
    gen_cls = GENERATORS.get(barcode_type, Code128Generator)
    try:
        return gen_cls().generate(code)
    except Exception:
        # Graceful fallback to Code-128
        if gen_cls != Code128Generator:
            return Code128Generator().generate(code)
        raise
