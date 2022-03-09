import Arduino
import Oscilloscope
import VNA

vnachanneloffset = 1 << 6
scopechanneloffset = 1 << 7

max_channel = 64

scope_sample_interval_ns = 1 # sampling period of oscilloscope

class CatheterTester:
    def __init__(self):
        self.arduino = Arduino.Arduino()
        self.scope = Oscilloscope.Oscilloscope()
        self.vna = VNA.VNA()
        self.channel = -1

        if not self.arduino.IsConnected():  # if could not connect to the arduino
            print("Could Not Connect To the Arduino, Exiting")
            input("Press Any Key To Exit")
            exit() # leave the program
                
    def ImpedanceTest(self, filename: str = None) -> bool:

        if self.vna is None:
            return

        self.vna.SetFileName(filename + str(self.channel + 1))
        self.vna.Sweep()

    def PulseEchoTest(self, channel: int = 1, duration_us: float = 6.0, filename: str = "cath.csv") -> bool:
        
        if not self.scope.IsConnected():
            return
        
        self.scope.CaptureWaveform(channel, duration_us)
        self.scope.CalculateFFT()
        self.scope.WriteDataToCSVFile(filename + str(self.channel + 1))

    def SetChannel(self, channel: int):

        if(channel < 0):
            return
            
        self.channel = channel % max_channel

        relay_ch = (channel & 0x30) >> 4 # get the two bit relay channel 
        channel &= ~0x30 # clear the bits of the relay channel
        
        # custom relay channel mapping, see Jesus
        if relay_ch == 0x3:
            relay_ch = 0x2
        elif relay_ch == 0x2:
            relay_ch = 0x3
        elif relay_ch == 0x1:
            relay_ch = 0x1
        else:
            relay_ch = 0x0

        channel |= relay_ch << 4 # put the correct index in

        self.arduino.Write(channel.to_bytes(1, 'big'))
        


if __name__ == "__main__":
    pass
