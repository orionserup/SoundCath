import Arduino
import Oscilloscope
import VNA

vnachanneloffset = 1 << 6
scopechanneloffset = 1 << 7

scope_sample_interval_ns = 1 # sampling period of oscilloscope

class CatheterTester:
    def __init__(self):
        self.arduino = Arduino.Arduino()
        self.scope = Oscilloscope.Oscilloscope()
        self.vna = VNA.VNA()
        self.channel = -1

        if not self.Arduino.IsConnected():  # if could not connect to the arduino
            print("Could Not Connect To the Arduino, Exiting")
            input("Press Any Key To Exit")
            exit() # leave the program
                
    def ImpedanceTest(self, filename: str) -> bool:
        pass

    def PulseEchoTest(self, channel: int = 1, duration_us: float = 6.0, filename: str = "cath.csv") -> bool:
        pass

    def SetChannel(self, channel: int):
        self.arduino.Write(channel.to_bytes(1, 'big'))


if __name__ == "__main__":
    tester


