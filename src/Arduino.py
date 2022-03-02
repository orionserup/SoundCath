import serial
from serial.tools.list_ports import comports

class Arduino:
    def __init__(self):
        all_ports = comports()
        print("Listing Serial Ports: ")
        
        for port, info, _ in all_ports: # for every detected port add it to a set of port names
            print(str(info))

            if "Arduino" in str(info):
                self.port = serial.Serial(port, baudrate = 115200, timeout = .5)
                print(f"Connected to Arduino on Port {port}\n")
                return

        print("Could Not Connect To A Valid Arduino Serial Port") # if we couldn't find a working Arduino then print this message
        self.port = None

    def IsConnected(self) -> bool:
        return self.port != None

    def Write(self, data: bytes) -> int:
        if self.port is not None:
            time.sleep(.01)
            self.port.write(data)
            return len(data)

        return 0

    def Read(self, size: int) -> bytes:
        if self.port is not None:
            return self.port.read(size)

    def ReadLine(self) -> bytes:
        if self.port is not None:
            return self.port.readline()
