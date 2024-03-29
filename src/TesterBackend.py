import Arduino
import Oscilloscope
import os
import numpy as np
import VNA
import math
import matplotlib.pyplot as plt

# user edittable pass fail criterion
# the number of channels we are testing
max_channel = 64

# the upper threshhold of the capacitance for the dongle test, must be less than this
dongle_upper_thresh = 340e-12    
# the lower threshold of the capacitance for the dongle test, must be greater than this
dongle_lower_thresh = 290e-12
# the frequency to test the dongle at
dongle_freq = 800e3

# impedance test capacitance upper threshhold, must be less than this
channel_upper_thresh = 750e-12
# impedance test capacitance lower threshold, must be greater than this
channel_lower_thresh = 700e-12
# frequency to test the impedance at
channel_freq = 800e3

# pulse echo when to start the waveform capture
scope_window_start_us = 49.6
# pulse echo how wide of a window to examine
scope_window_width_us = .9

# pulse echo fft when to start the window
fft_window_start = 2e6
# pulse echo fft the window of the fft we want to look at
fft_window_width = 8e6

# pulse echo vpp lower threshold, must be higher than this
vpp_lower_thresh = 50.0e-3
# pulse echo upper threshold, must be lower than this
vpp_upper_thresh = 140.0e-3

# pulse echo bandwidth lower threshold, must be greater than this
bandwidth_lower_thresh = 0.0
# pulse echo bandwidth upper threshold, must be less than this
bandwidth_upper_thresh = 10e6

# center frequency lower threshold, must be greater than this
peak_freq_lower_thresh = 5e6
# center frequency upper threshold, must be less than this
peak_freq_upper_thresh = 8e6

scope_sample_interval_ns = 1 # sampling period of oscilloscope

# do not edit past here #

vnachanneloffset = 1 << 7
scopechanneloffset = 1 << 6

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
            c = -1 / (2 * math.pi * data["Z"][i].imag * dongle_freq) # if there is an entry with the test frequency calculate the capacitance
            print(f"Capacitance: {c * 1e12: .2f}pF")
            if c < dongle_upper_thresh and c > dongle_lower_thresh: # 1 / wC = im(Z)  # if we are within the thresholds then we are good
                return [True, c] # Passed the test
                
            return [False, c] # Failed the Test

        return [False, 0]
        
    def ImpedanceTest(self, channel = 1, filename: str = None) -> list[bool, float]:

        if self.vna is None:
            return False # if the VNA wasn't initialized we can't pass the test
        
        self.vna.SetFileName(filename + str(channel)) # set the filename to "{filename} {channel} s11.s1p"
        
        self.vna.SetStartFreq(channel_freq) # we only want to test one frequency
        self.vna.SetStopFreq(channel_freq)
        self.vna.SetNumPoints(1)
        self.vna.SetSweepParameters(["s11"]) # we are looking for impedance
        
        self.vna.Sweep() # sweep and save the values to an s1p file
        
        data = VNA.GrabS1PData(filename + str(channel) + "s11.s1p") # convert the generated csv file and pull the data

        print(data)

        i = data["Frequency"].index(channel_freq) # if we find the frequency we wanted in the data set

        if i is not None:
            c = -1 / (2 * math.pi * data["Z"][i].imag * channel_freq) # if there is an entry with the test frequency calculate the capacitance
            print(f"Capacitance: {c * 1e12: .2f} pF")
            if c < channel_upper_thresh and c > channel_lower_thresh: # 1 / wC = im(Z)  # if we are within the thresholds then we are good
                return [True, c] # Passed the test
                
        return [False, c] # if we didnt pass we failed
        
        
    def PulseEchoTest(self, scopechannel: int = 1, channel = 1, filename: str = "cath.csv") -> list[bool, float, float, float]:
        
        if not self.scope.IsConnected(): # if we aren't connected to the scope then we automatically fail
            return False, None, None, None
        
        self.scope.CaptureWaveform(scopechannel) # capture the waveform from the screen
        self.scope.WindowWaveform(scope_window_start_us, scope_window_width_us)
        data = self.scope.GetWaveform()

        minimum = min(data["Voltage"]) # find the minimum voltage of the waveform
        maximum = max(data["Voltage"]) # find the maximum voltage of the waveform
        
        vpp = maximum - minimum # get the peak to peak maximum 

        self.scope.CalculateFFT() # calculate the fft of the waveform      
        self.scope.WindowFFT(fft_window_start, fft_window_width)
        fft = self.scope.GetFFT()

        
        #self.scope.WriteDataToCSVFile(filename + str(self.channel + 1)) # Save all of the Data to a CSV File

        # plot the waveform and fft and save it
        plt.plot(data["Time"], data["Voltage"])
        plt.xlabel("Time")
        plt.ylabel("Voltage")
        plt.savefig(filename + "wave" + str(channel) + ".png")
        plt.close()

        plt.plot(fft["Frequency"], fft["Amplitude"])
        plt.xlabel("Frequency")
        plt.ylabel("Amplitude")
        plt.savefig(filename + "fft" + str(channel) + ".png")
        plt.close()

        # Get the FFT
        fft = self.scope.GetFFT()
        maxamp = fft["Amplitude"].max() # find the maximum amplitude over the spectrum
        maxindex = np.where(fft['Amplitude'] == maxamp)[0][0] # find where the maximum amplitude is at

        thresh = .707 * maxamp # -3db cutoff
        
        left = maxindex # start the bandedges at the center frequency
        right = maxindex 

        while fft["Amplitude"][left] > thresh: # we go until we hit -3db going left
            if left <= 0:
                break
            left -= 1

        while fft["Amplitude"][right] > thresh: # we go until we hit -3db going right
            if right >= len(fft["Amplitude"]) - 1:
                break 
            right += 1

        # left edge is on the lower band edge and right is on the upper band edge

        bandwidth = fft["Frequency"][right] - fft["Frequency"][left] # bandwidth is the distance between the upper and lower bandedges
        peak = fft["Frequency"][maxindex] # the center frequency is where the maximum is

        print(f"Vpp: {vpp} Bandwidth: {bandwidth} Peak Frequency: {peak}")        # debug message
        
        # check all of the thresholds and return if it passed and the tested values

        # if vpp < .04 we have a dead element and thus return failure, the rest of the values dont matter
        if vpp <= .04:
            return [False, 0, 0, 0]

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
