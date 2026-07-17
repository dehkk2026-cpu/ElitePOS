import os
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

class ReceiptRenderer:
    def __init__(self):
        self.printer_width = 384
        self.font_path = None
        android_fonts = [
            '/system/fonts/NotoNaskhArabic-Regular.ttf',
            '/system/fonts/DroidKufi-Regular.ttf',
            '/system/fonts/Roboto-Regular.ttf'
        ]
        for font in android_fonts:
            if os.path.exists(font):
                self.font_path = font
                break
                
    def get_font(self, size=24):
        try:
            if self.font_path:
                return ImageFont.truetype(self.font_path, size)
            return ImageFont.load_default()
        except:
            return ImageFont.load_default()

    def process_arabic(self, text):
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)

    def generate_receipt(self, cart_items, total, is_z_report=False):
        header_height = 150
        item_height = 40
        footer_height = 150
        img_height = header_height + (len(cart_items) * item_height) + footer_height

        img = Image.new('RGB', (self.printer_width, img_height), color='white')
        draw = ImageDraw.Draw(img)
        
        font_large = self.get_font(32)
        font_normal = self.get_font(24)

        y_offset = 20

        title = self.process_arabic("تقرير Z" if is_z_report else "نقطة البيع - فاتورة")
        title_bbox = draw.textbbox((0, 0), title, font=font_large)
        title_x = (self.printer_width - (title_bbox[2] - title_bbox[0])) / 2
        draw.text((title_x, y_offset), title, font=font_large, fill='black')
        
        y_offset += 60
        draw.line([(20, y_offset), (self.printer_width-20, y_offset)], fill='black', width=2)
        y_offset += 20

        for item in cart_items:
            name_text = self.process_arabic(item['name'])
            price_text = f"{item['qty']} x ${item['price']:.2f}"
            
            draw.text((20, y_offset), name_text, font=font_normal, fill='black')
            
            price_bbox = draw.textbbox((0, 0), price_text, font=font_normal)
            price_x = self.printer_width - 20 - (price_bbox[2] - price_bbox[0])
            draw.text((price_x, y_offset), price_text, font=font_normal, fill='black')
            
            y_offset += item_height

        y_offset += 20
        draw.line([(20, y_offset), (self.printer_width-20, y_offset)], fill='black', width=2)
        y_offset += 20

        total_label = self.process_arabic("الإجمالي: ")
        total_val = f"${total:.2f}"
        draw.text((20, y_offset), total_label, font=font_large, fill='black')
        
        val_bbox = draw.textbbox((0, 0), total_val, font=font_large)
        val_x = self.printer_width - 20 - (val_bbox[2] - val_bbox[0])
        draw.text((val_x, y_offset), total_val, font=font_large, fill='black')

        y_offset += 60
        footer = self.process_arabic("شكراً لزيارتكم!")
        f_bbox = draw.textbbox((0, 0), footer, font=font_normal)
        f_x = (self.printer_width - (f_bbox[2] - f_bbox[0])) / 2
        draw.text((f_x, y_offset), footer, font=font_normal, fill='black')

        return self._image_to_escpos(img)

    def _image_to_escpos(self, img):
        img = img.convert('1')
        width, height = img.size
        
        if width % 8 != 0:
            width = (width // 8 + 1) * 8
            new_img = Image.new('1', (width, height), color=1)
            new_img.paste(img, (0, 0))
            img = new_img

        bytes_per_row = width // 8
        
        header = bytearray([0x1D, 0x76, 0x30, 0x00, 
                            bytes_per_row % 256, bytes_per_row // 256,
                            height % 256, height // 256])
        
        img_data = bytearray()
        pixels = img.load()
        
        for y in range(height):
            for x in range(0, width, 8):
                byte_val = 0
                for bit in range(8):
                    if x + bit < width:
                        pixel_is_black = (pixels[x + bit, y] == 0)
                        if pixel_is_black:
                            byte_val |= (1 << (7 - bit))
                img_data.append(byte_val)

        escpos_data = bytearray([0x1B, 0x40]) + header + img_data + bytearray([0x0A, 0x0A, 0x0A, 0x0A, 0x1D, 0x56, 0x41, 0x10])
        return bytes(escpos_data)