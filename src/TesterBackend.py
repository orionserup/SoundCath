import Arduino
import Oscilloscope
import os
import numpy as np
import VNA
import math

vnachanneloffset = 1 << 6
scopechanneloffset = 1 << 7

max_channel = 64

dongle_upper_thresh = 103e-12
dongle_lower_thresh = 90e-12
dongle_freq = 800e3

channel_upper_thresh = 100e-12
channel_lower_thresh = 80e-12
channel_freq = 500e3

scope_sample_interval_ns = 1 # sampling period of oscilloscope

class CatheterTester:
    def __init__(self):
        self.arduino = Arduino.Arduino() # we have an arduino 
        self.scope = Oscilloscope.Oscilloscope() # an oscilloscope
        self.vna = VNA.VNA() # and a VNA
        self.channel = -1 # start with no channel being connected 

        if not self.arduino.IsConnected():  # if could not connect to the arduino
            print("Could Not Connect To the Arduino, Exiting")
            input("Press Any Key To Exit")
            exit() # leave the program
            
    def DongleTest(self, filename: str = None) -> bool:
        
        if self.vna is None:  # if we didnt initialze the VNA we can't run the test
            return False
        
        self.vna.SetStartFreq(dongle_freq) # we only want to test one frequency
        self.vna.SetStopFreq(dongle_freq)
        self.vna.SetNumPoints(1)
        self.vna.SetSweepParameters(["s11"]) # we want to test for impedance, which is calculated from S11
  
        self.vna.SetFileName(filename + str(self.channel + 1) + "dongle") # set the filename to what was provided as well as the channel and dongle indicator 
            
        self.vna.Sweep() # run the sweep 
  
        data = VNA.ConvertS1PToCSV(filename + str(self.channel + 1) + "dongles11.s1p") # pull the data from the s1p file, write it to CSV
        i = data["Frequency"].index(dongle_freq) # find the index from the data with the test frequency
        if i is not None:
            c = 1 / (2 * math.pi * data["Z"][i].imag * dongle_freq) # if there is an entry with the test frequency calculate the capacitance
            if c < dongle_upper_thresh and c > dongle_lower_thresh: # 1 / wC = im(Z)  # if we are within the thresholds then we are good
                return True # Passed the test
                
        return False # Failed the Test
        
    def ImpedanceTest(self, filename: str = None) -> bool:

        if self.vna is None:
            return False # if the VNA wasn't initialized we can't pass the test
        
        self.vna.SetFileName(filename + str(self.channel + 1)) # set the filename to "{filename} {channel} s11.s1p"
        
        self.vna.SetStartFreq(channel_freq) # we only want to test one frequency
        self.vna.SetStopFreq(channel_freq)
        self.vna.SetNumPoints(1)
        self.vna.SetSweepParameters(["s11"]) # we are looking for impedance
        
        self.vna.Sweep() # sweep and save the values to an s1p file
        
        data = VNA.ConvertS1PToCSV(filename + str(self.channel + 1) + "s11.s1p") # convert the generated csv file and pull the data
        i = data["Frequency"].index(channel_freq) # if we find the frequency we wanted in the data set
        if i is not None:
            z = data["Z"][i] # get the corresponding impedance with the frequency
            if abs(z) > channel_lower_thresh and abs(z) < channel_upper_thresh: # if we are within the threshold then we pass the test
                return True # return a pass
                
        return False # if we didnt pass we failed
        
        
    def PulseEchoTest(self, channel: int = 1, filename: str = "cath.csv", duration_us: float = 6.0, ) -> bool:
        
        if not self.scope.IsConnected(): # if we aren't connected to the scope then we automatically fail
            return False
        
        data = self.scope.CaptureWaveform(channel, duration_us) # capture the waveform from the screen
        
        minimum = min(data["Voltage"]) # find the minimum voltage of the waveform
        maximum = max(data["Voltage"]) # find the maximum voltage of the waveform
        
        vpp = maximum - minimum; # get the peak to peak maximum 
        
        self.scope.CalculateFFT() # calculate the fft of the waveform
        self.scope.WriteDataToCSVFile(filename + str(self.channel + 1)) # Save all of the Data to a CSV File
        
        return True

    def SetChannel(self, channel: int):

        if(channel < 0):
            return

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
