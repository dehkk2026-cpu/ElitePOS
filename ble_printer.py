import time
from kivy.utils import platform

class BLEPrinterManager:
    def __init__(self):
        self.connected = False
        self.device_address = None
        
        if platform == 'android':
            from jnius import autoclass
            self.BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
            self.Context = autoclass('android.content.Context')
            self.UUID = autoclass('java.util.UUID')
            self.adapter = self.BluetoothAdapter.getDefaultAdapter()
            self.gatt = None
            self.write_char = None
        else:
            self.adapter = None

    def is_connected(self):
        return self.connected

    def start_scan(self, callback):
        if platform != 'android' or not self.adapter:
            callback("Test_Printer_MTP", "00:11:22:33:44:55")
            return

        bonded_devices = self.adapter.getBondedDevices().toArray()
        for device in bonded_devices:
            callback(device.getName(), device.getAddress())

    def connect(self, mac_address):
        if platform != 'android' or not self.adapter:
            self.connected = True
            return True

        try:
            device = self.adapter.getRemoteDevice(mac_address)
            spp_uuid = self.UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
            self.socket = device.createRfcommSocketToServiceRecord(spp_uuid)
            self.adapter.cancelDiscovery()
            self.socket.connect()
            self.output_stream = self.socket.getOutputStream()
            self.connected = True
            self.device_address = mac_address
            return True
        except Exception as e:
            print(f"BLE Connect Error: {e}")
            self.connected = False
            return False

    def disconnect(self):
        if platform == 'android' and hasattr(self, 'socket') and self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connected = False

    def send_data(self, data_bytes):
        if not self.connected:
            return False
            
        if platform != 'android':
            print(f"Desktop Dummy Print: {len(data_bytes)} bytes sent.")
            return True

        try:
            chunk_size = 1024
            for i in range(0, len(data_bytes), chunk_size):
                chunk = data_bytes[i:i+chunk_size]
                self.output_stream.write(chunk)
                self.output_stream.flush()
                time.sleep(0.05)
            return True
        except Exception as e:
            print(f"Send Data Error: {e}")
            self.connected = False
            return False