import Arduino
import Oscilloscope
import os
import numpy as np
import VNA
import math
import matplotlib.pyplot as plt

vnachanneloffset = 1 << 7
scopechanneloffset = 1 << 6

max_channel = 5

dongle_upper_thresh = 103e-12    
dongle_lower_thresh = 90e-12
dongle_freq = 800e3

channel_upper_thresh = 100e-12
channel_lower_thresh = 80e-12
channel_freq = 800e3

scope_window_start_us = 4.95
scope_window_width_us = .2

vpp_lower_thresh = 0.0
vpp_upper_thresh = 10.0

bandwidth_lower_thresh = 0.0
bandwidth_upper_thresh = 10e6

peak_freq_lower_thresh = 0.0
peak_freq_upper_thresh = 10e6

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
            
    def DongleTest(self, channel, filename: str = None) -> list[bool, float]:
        
        if self.vna is None:  # if we didnt initialze the VNA we can't run the test
            return False
        
        self.vna.SetStartFreq(dongle_freq) # we only want to test one frequency
        self.vna.SetStopFreq(dongle_freq)
        self.vna.SetNumPoints(1)
        self.vna.SetSweepParameters(["s11"]) # we want to test for impedance, which is calculated from S11
  
        self.vna.SetFileName(filename + str(channel + 1) + "dongle") # set the filename to what was provided as well as the channel and dongle indicator 
            
        self.vna.Sweep() # run the sweep 
  
        data = VNA.GrabS1PData(filename + str(channel + 1) + "dongles11.s1p") # pull the data from the s1p file, write it to CSV

        print(data)

        i = data["Frequency"].index(dongle_freq) # find the index from the data with the test frequency

        if i is not None:
            c = 1 / (2 * math.pi * data["Z"][i].imag * dongle_freq) # if there is an entry with the test frequency calculate the capacitance
            if c < dongle_upper_thresh and c > dongle_lower_thresh: # 1 / wC = im(Z)  # if we are within the thresholds then we are good
                return [True, c] # Passed the test
                
        return [False, c] # Failed the Test
        
    def ImpedanceTest(self, channel = 1, filename: str = None) -> list[bool, float]:

        if self.vna is None:
            return False # if the VNA wasn't initialized we can't pass the test
        
        self.vna.SetFileName(filename + str(channel)) # set the filename to "{filename} {channel} s11.s1p"
        
        self.vna.SetStartFreq(channel_freq) # we only want to test one frequency
        self.vna.SetStopFreq(channel_freq)
        self.vna.SetNumPoints(1)
        self.vna.SetSweepParameters(["s11"]) # we are looking for impedance
        
        self.vna.Sweep() # sweep and save the values to an s1p file
        
        data = VNA.GrabS1PData(filename + str(channel + 1) + "s11.s1p") # convert the generated csv file and pull the data

        print(data)

        i = data["Frequency"].index(channel_freq) # if we find the frequency we wanted in the data set

        if i is not None:
            c = 1 / (2 * math.pi * data["Z"][i].imag * channel_freq) # if there is an entry with the test frequency calculate the capacitance
            if c < dongle_upper_thresh and c > dongle_lower_thresh: # 1 / wC = im(Z)  # if we are within the thresholds then we are good
                return [True, c] # Passed the test
                
        return [False, c] # if we didnt pass we failed
        
        
    def PulseEchoTest(self, scopechannel: int = 1, channel = 1, filename: str = "cath.csv") -> list[bool, float, float, float]:
        
        if not self.scope.IsConnected(): # if we aren't connected to the scope then we automatically fail
            return False, None, None, None
        
        self.scope.CaptureWaveform(scopechannel) # capture the waveform from the screen
        data = self.scope.WindowWaveform(scope_window_start_us, scope_window_width_us)

        minimum = min(data["Voltage"]) # find the minimum voltage of the waveform
        maximum = max(data["Voltage"]) # find the maximum voltage of the waveform
        
        vpp = maximum - minimum # get the peak to peak maximum 

        self.scope.CalculateFFT() # calculate the fft of the waveform      
        fft = self.scope.WindowFFT(1e6, 8e6)  

        maxamp = np.amax(fft['Amplitude'])
        maxindex = np.where(fft['Amplitude'] == maxamp)

        leftband = fft['Frequency'][maxindex[0][0]]
        rightband = fft['Frequency'][maxindex[0][0]]
        
        for i in range(maxindex[0][0], len(fft['Frequency'])):
            if fft['Amplitude'][i] <= maxamp / 2:
                rightband = fft["Frequency"][i - 1]
                break

        for i in range(maxindex[0][0], 0, -1):
            if fft['Amplitude'][i] <= maxamp / 2:
                leftband = fft["Frequency"][i + 1]
                break

        bandwidth = rightband - leftband
        peak = (rightband + leftband) / 2

        print(f"Vpp: {vpp} Bandwidth: {bandwidth} Peak Frequency: {peak}")        
        
        #self.scope.WriteDataToCSVFile(filename + str(self.channel + 1)) # Save all of the Data to a CSV File
        plt.plot(data["Time"], data["Voltage"])
        plt.xlabel("Time")
        plt.ylabel("Voltage")
        plt.savefig(filename + "wave" + str(channel) + ".png")

        plt.plot(fft["Frequency"], fft["Amplitude"])
        plt.xlabel("Frequency")
        plt.ylabel("Amplitude")
        plt.savefig(filename + "fft" + str(channel) + ".png")

        if vpp < vpp_lower_thresh or vpp > vpp_upper_thresh:
            return [False, vpp, bandwidth, peak]

        if bandwidth < bandwidth_lower_thresh or bandwidth > bandwidth_upper_thresh:
            return [False, vpp, bandwidth, peak]

        if peak < peak_freq_lower_thresh or peak > peak_freq_upper_thresh:
            return [False, vpp, bandwidth, peak]
        
        return [True, vpp, bandwidth, peak]

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
