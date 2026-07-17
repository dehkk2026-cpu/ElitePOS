import os
import kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineAvatarIconListItem, IconLeftWidget
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, ListProperty

from pos_storage import POSStorage
from ble_printer import BLEPrinterManager
from receipt_renderer import ReceiptRenderer

if platform == 'android':
    from android.permissions import request_permissions, Permission
    from jnius import autoclass
    # System Native Beep for Android
    AudioManager = autoclass('android.media.AudioManager')
    ToneGenerator = autoclass('android.media.ToneGenerator')
    tone_gen = ToneGenerator(AudioManager.STREAM_ALARM, 100)
else:
    tone_gen = None

Window.softinput_mode = "below_target"

class CartItem(MDCard):
    item_id = StringProperty()
    name = StringProperty()
    qty = NumericProperty(1)
    price = NumericProperty(0.0)

class ProductItem(MDCard):
    item_id = StringProperty()
    name = StringProperty()
    price = NumericProperty(0.0)
    category = StringProperty()

class CashierScreen(MDScreen):
    cart = ListProperty([])

    def on_enter(self):
        self.load_products()
        self.update_totals()

    def load_products(self):
        grid = self.ids.products_grid
        grid.clear_widgets()
        products = self.app.storage.get_products()
        for p in products:
            item = ProductItem(
                item_id=p['id'],
                name=p['name'],
                price=p['price'],
                category=p['category']
            )
            item.bind(on_release=self.add_to_cart)
            grid.add_widget(item)

    def add_to_cart(self, product_card):
        for item in self.cart:
            if item['id'] == product_card.item_id:
                item['qty'] += 1
                self.render_cart()
                return
        
        self.cart.append({
            'id': product_card.item_id,
            'name': product_card.name,
            'price': product_card.price,
            'qty': 1
        })
        self.render_cart()

    def render_cart(self):
        cart_list = self.ids.cart_list
        cart_list.clear_widgets()
        for i, item in enumerate(self.cart):
            ci = CartItem(
                item_id=item['id'],
                name=item['name'],
                qty=item['qty'],
                price=item['price']
            )
            # Select item logic can be added here
            cart_list.add_widget(ci)
        self.update_totals()

    def set_quantity(self, qty):
        if not self.cart:
            return
        # Apply to the last added item for simplicity in fast POS
        if qty == 'Clear':
            self.cart.pop()
        else:
            self.cart[-1]['qty'] = int(qty)
        self.render_cart()

    def clear_cart(self):
        self.cart = []
        self.render_cart()

    def update_totals(self):
        total = sum(item['qty'] * item['price'] for item in self.cart)
        self.ids.total_label.text = f"Total: ${total:.2f}"

    def play_beep(self):
        if tone_gen:
            tone_gen.startTone(ToneGenerator.TONE_PROP_BEEP, 200)

    def pay_and_print(self):
        if not self.cart:
            self.app.show_error("Cart is empty!")
            return

        self.play_beep()
        total = sum(item['qty'] * item['price'] for item in self.cart)
        
        # Save Sale
        self.app.storage.record_sale(total)
        
        # Print
        if self.app.printer.is_connected():
            receipt_bytes = self.app.renderer.generate_receipt(self.cart, total)
            self.app.printer.send_data(receipt_bytes)
        else:
            self.app.show_error("Sale recorded. Printer not connected.")

        self.clear_cart()

class AdminScreen(MDScreen):
    def on_enter(self):
        self.update_stats()
        self.load_admin_products()
        self.ids.printer_status.text = f"Status: {'Connected' if self.app.printer.is_connected() else 'Disconnected'}"

    def update_stats(self):
        stats = self.app.storage.get_stats()
        self.ids.total_orders.text = str(stats['total_orders'])
        self.ids.total_sales.text = f"${stats['total_sales']:.2f}"

    def load_admin_products(self):
        lst = self.ids.admin_product_list
        lst.clear_widgets()
        for p in self.app.storage.get_products():
            lst.add_widget(OneLineAvatarIconListItem(text=f"{p['name']} - ${p['price']}"))

    def add_product(self):
        name = self.ids.prod_name.text
        price = self.ids.prod_price.text
        if name and price:
            self.app.storage.add_product({
                "id": str(len(self.app.storage.get_products()) + 1),
                "name": name,
                "price": float(price),
                "category": "General"
            })
            self.ids.prod_name.text = ""
            self.ids.prod_price.text = ""
            self.load_admin_products()

    def close_shift(self):
        stats = self.app.storage.get_stats()
        # Print Z Report
        if self.app.printer.is_connected():
            z_report = [{"name": "TOTAL SALES", "qty": stats['total_orders'], "price": stats['total_sales']}]
            receipt_bytes = self.app.renderer.generate_receipt(z_report, stats['total_sales'], is_z_report=True)
            self.app.printer.send_data(receipt_bytes)
        
        self.app.storage.clear_stats()
        self.update_stats()
        self.app.show_error("Shift Closed. Stats Reset.")

    def scan_bluetooth(self):
        self.ids.printer_status.text = "Scanning..."
        self.app.printer.start_scan(self.on_device_found)

    def on_device_found(self, name, address):
        # Update UI with found devices
        Clock.schedule_once(lambda dt: self.add_device_to_list(name, address))

    def add_device_to_list(self, name, address):
        lst = self.ids.ble_devices_list
        item = OneLineAvatarIconListItem(text=f"{name} ({address})")
        item.bind(on_release=lambda x: self.connect_printer(address))
        lst.add_widget(item)

    def connect_printer(self, address):
        self.ids.printer_status.text = "Connecting..."
        success = self.app.printer.connect(address)
        if success:
            self.ids.printer_status.text = f"Connected to {address}"
            self.app.storage.save_printer(address, "BLE Printer")
        else:
            self.ids.printer_status.text = "Connection Failed"

class MainPOSApp(MDApp):
    dialog = None

    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "BlueGray"
        
        # Initialize Core Modules
        self.storage = POSStorage()
        self.printer = BLEPrinterManager()
        self.renderer = ReceiptRenderer()

        # Permissions for Android
        if platform == 'android':
            request_permissions([
                Permission.BLUETOOTH, Permission.BLUETOOTH_ADMIN,
                Permission.BLUETOOTH_CONNECT, Permission.BLUETOOTH_SCAN,
                Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION
            ])

        Builder.load_file('kivy_ui.kv')
        sm = MDScreenManager()
        
        cashier = CashierScreen(name='cashier')
        cashier.app = self
        
        admin = AdminScreen(name='admin')
        admin.app = self
        
        sm.add_widget(cashier)
        sm.add_widget(admin)
        return sm

    def show_error(self, text):
        if not self.dialog:
            self.dialog = MDDialog(
                text=text,
                buttons=[MDFlatButton(text="OK", on_release=lambda x: self.dialog.dismiss())]
            )
        self.dialog.text = text
        self.dialog.open()

if __name__ == '__main__':
    MainPOSApp().run()