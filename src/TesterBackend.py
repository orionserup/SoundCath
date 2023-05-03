import Arduino
import Oscilloscope
import os
import numpy as np
import VNA
import math
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt

# user edittable pass fail criterion
# the number of channels we are testing
max_channel = [32, 64, 96]

# the upper threshhold of the capacitance for the dongle test, must be less than this
dongle_upper_thresh = [315e-12, 315e-12, 315e-12]    
# the lower threshold of the capacitance for the dongle test, must be greater than this
dongle_lower_thresh = [270e-12, 270e-12, 270e-12]
# the frequency to test the dongle at
dongle_freq = 800e3

# impedance test capacitance upper threshhold, must be less than this
channel_upper_thresh = [800e-12, 800e-12, 920e-12]
# impedance test capacitance lower threshold, must be greater than this
channel_lower_thresh = [700e-12, 715e-12, 750e-12]
# frequency to test the impedance at
channel_freq = 800e3

# pulse echo when to start the waveform capture
scope_window_start_us = 49.6
# pulse echo how wide of a window to examine
scope_window_width_us = 3.2

# pulse echo fft when to start the window
fft_window_start = 2e6
# pulse echo fft the window of the fft we want to look at
fft_window_width = 6e6

# pulse echo vpp lower threshold, must be higher than this
vpp_lower_thresh = [65.0e-3, 65.0e-3, 65.0e-3]
# pulse echo upper threshold, must be lower than this
vpp_upper_thresh = [315.0e-3, 315.0e-3, 315.0e-3]

# pulse echo bandwidth lower threshold, must be greater than this
bandwidth_lower_thresh = [0.0, 0.0, 0.0]
# pulse echo bandwidth upper threshold, must be less than this
bandwidth_upper_thresh = [10e6, 10e6, 10e6]

# center frequency lower threshold, must be greater than this
peak_freq_lower_thresh = [5e6, 5e6, 5e6]
# center frequency upper threshold, must be less than this
peak_freq_upper_thresh = [8e6, 8e6, 8e6]

# do not edit past here #

vnachanneloffset = 1 << 7
scopechanneloffset = 1 << 6

class CatheterTester:
    def __init__(self):
        self.arduino = Arduino.Arduino() # we have an arduino 
        self.scope = Oscilloscope.Oscilloscope() # an oscilloscope
        self.vna = VNA.VNA() # and a VNA
        self.channel = -1 # start with no channel being connected 

        # if not self.arduino.IsConnected():  # if could not connect to the arduino
        #     print("Could Not Connect To the Arduino, Exiting")
        #     input("Press Any Key To Exit")
        #     exit() # leave the program
            
    def DongleTest(self, channel: int , maxchannel: int = 96, filename: str = None) -> list[bool, float]:
        
        if self.vna is None:  # if we didnt initialze the VNA we can't run the test
            return [False, 0, 0]
        
        self.SetChannel(channel, maxchannel, True)
        
        self.vna.SetStartFreq(0) # we only want to test one frequency
        self.vna.SetStopFreq(100e6)
        self.vna.SetNumPoints(10000)
        self.vna.SetSweepParameters(["s11"]) # we are looking for impedance
        self.vna.SetScale("lin")
        
        try:
        
            self.vna.Sweep() # sweep and save the values to an s1p file
            
            data = VNA.GrabS1PData(filename + str(channel) + "s11.s1p") # convert the generated csv file and pull the data
            
            char_z = 0
            char_freq = 0
            for i, z in enumerate(data["Z"]):
                if np.imag(z) < .01 or np.imag(z) > -.01:
                    char_z = data["Z"][i / 2]
                    char_freq = data["Frequency"][i]
                    break
                
            print(f"Crossing Frequency: {char_freq}")
            print(f"Characteristic Impedance: {char_z}")

            i = data["Frequency"].index(dongle_freq) # find the index from the data with the test frequency
            idx = max_channel.index(maxchannel)

            if i is not None:
                c = -1 / (2 * math.pi * data["Z"][i].imag * dongle_freq) # if there is an entry with the test frequency calculate the capacitance
                print(f"Capacitance: {c * 1e12: .2f}pF")
                if c < dongle_upper_thresh[idx] and c > dongle_lower_thresh[idx]: # 1 / wC = im(Z)  # if we are within the thresholds then we are good
                    return [True, c, char_z] # Passed the test
                else:
                    return [False, c, char_z] # Failed the Test
                
        except Exception as e:
            print(e)

        return [False, 0, 0]
        
    def ImpedanceTest(self, channel: int, maxchannel: int = 96, filename: str = None) -> list[bool, float]:

        if self.vna is None:
            return [False, 0, 0] # if the VNA wasn't initialized we can't pass the test
        
        self.SetChannel(channel, maxchannel, True)
        
        self.vna.SetFileName(filename + str(channel)) # set the filename to "{filename} {channel} s11.s1p"
        
        self.vna.SetStartFreq(0) # we only want to test one frequency
        self.vna.SetStopFreq(100e6)
        self.vna.SetNumPoints(10000)
        self.vna.SetSweepParameters(["s11"]) # we are looking for impedance
        self.vna.SetScale("lin")
        
        try:
        
            self.vna.Sweep() # sweep and save the values to an s1p file
            
            data = VNA.GrabS1PData(filename + str(channel) + "s11.s1p") # convert the generated csv file and pull the data
            
            char_z = 0
            char_freq = 0
            for i, z in enumerate(data["Z"]):
                if np.imag(z) < .01 or np.imag(z) > -.01:
                    char_z = data["Z"][i / 2]
                    char_freq = data["Frequency"][i]
                    break
                
            print(f"Crossing Frequency: {char_freq}")
            print(f"Characteristic Impedance: {char_z}")

            i = data["Frequency"].index(channel_freq) # if we find the frequency we wanted in the data set
            idx = max_channel.index(maxchannel)

            if i is not None:
                c = -1 / (2 * math.pi * data["Z"][i].imag * channel_freq) # if there is an entry with the test frequency calculate the capacitance
                print(f"Capacitance: {c * 1e12: .2f} pF")
                if c < channel_upper_thresh[idx] and c > channel_lower_thresh[idx]: # 1 / wC = im(Z)  # if we are within the thresholds then we are good
                    return [True, c, char_z] # Passed the test
                else:
                    return [False, c, char_z] # Passed the test
                
        except Exception as e:
            print(e)
                
        return [False, 0, 0, 0] # if we didnt pass we failed
        
        
    def PulseEchoTest(self, scopechannel: int = 1, channel: int = 1, maxchannel: int = 96, filename: str = "cath.csv") -> list[bool, float, float, float]:
        
        self.SetChannel(channel, maxchannel, False)
        
        if not self.scope.IsConnected(): # if we aren't connected to the scope then we automatically fail
            return [False, None, None, None]
        
        self.scope.CaptureWaveform(scopechannel) # capture the waveform from the screen
        self.scope.WindowWaveform(scope_window_start_us, scope_window_width_us)
        data = self.scope.GetWaveform()       
        print(f"Number of Data Points: {len(data['Time'])}")

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
        
        sig = fft["Amplitude"]        
        
        dbamp = 20 * np.log10(sig / max(sig))
        print(f"FFT Length: {len(dbamp)}")        
        
        b, a = butter(3, .1)        
        dbamp = filtfilt(b, a, dbamp)           
        
        maxamp = dbamp.max() # find the maximum amplitude over the spectrum
        dbamp -= maxamp

        plt.plot(fft["Frequency"], dbamp)
        plt.xlabel("Frequency")
        plt.ylabel("Amplitude (dB)")
        plt.savefig(filename + "fft" + str(channel) + ".png")
        plt.close()

        # Get the FFT

        maxindex = np.where(dbamp == 0)[0][0] # find where the maximum amplitude is at

        thresh = -6 # -6db cutoff
        
        left = maxindex # start the bandedges at the center frequency
        right = maxindex 

        while dbamp[left] > thresh: # we go until we hit -3db going left
            if left <= 0:
                break
            left -= 1

        while dbamp[right] > thresh: # we go until we hit -3db going right
            if right >= len(dbamp) - 1:
                break 
            right += 1

        # left edge is on the lower band edge and right is on the upper band edge

        bandwidth = fft["Frequency"][right] - fft["Frequency"][left] # bandwidth is the distance between the upper and lower bandedges
        peak = fft["Frequency"][maxindex] # the center frequency is where the maximum is
        # bandwidth = bandwidth / peak

        print(f"Vpp: {vpp} Bandwidth: {bandwidth} Peak Frequency: {peak}")        # debug message
        
        # check all of the thresholds and return if it passed and the tested values
        idx = max_channel.index(maxchannel)

        # if vpp < .04 we have a dead element and thus return failure, the rest of the values dont matter
        if vpp <= .04:
            return [False, 0, 0, 0]

        if vpp < vpp_lower_thresh[idx] or vpp > vpp_upper_thresh[idx]:
            return [False, vpp, bandwidth, peak]

        if bandwidth < bandwidth_lower_thresh[idx] or bandwidth > bandwidth_upper_thresh[idx]:
            return [False, vpp, bandwidth, peak]    

        if peak < peak_freq_lower_thresh[idx] or peak > peak_freq_upper_thresh[idx]:
            return [False, vpp, bandwidth, peak]
        
        return [True, vpp, bandwidth, peak]

    def SetChannel(self, channel: int, maxchannel: int = 96, vna: bool = True):
        
        index = channel

        if maxchannel == 32:
            
            mapping_32 = [2, 8, 16, 22, 23, 24, 27, 28, 
                          33, 34, 36, 37, 38, 44, 45, 46,
                          47, 48, 49, 53, 57, 58, 59, 60, 
                          65, 79, 81, 82, 83, 84, 89, 91]
            
            index = mapping_32[index] - 1
        
        elif maxchannel == 64:        
            
            mapping_64 = [  2, 6, 7, 8, 15, 16, 21, 22, 
                            23, 24, 28, 33, 34, 36, 37,  
                            38, 40, 42, 43, 44, 45, 46, 47, 
                            48, 49, 50, 51, 52, 53, 57, 58, 
                            59, 60, 61, 62, 63, 64, 65, 69, 
                            70, 71, 72, 73, 74, 75, 76, 77, 78,  
                            79, 80, 81, 82, 83, 84, 85, 86,
                            87, 88, 89, 90, 91, 92, 93, 94]
            
            index = mapping_64[index] - 1
            
        if not vna:
            index = index | 0x80
            
        if index & 0x70 == 0x50:
            index = index & ~0x70
            index = index | 0x60

        print(f"Writing {index & 0xff} to Relays")
            
        self.arduino.Write(index.to_bytes(1, 'big'))

if __name__ == "__main__":
    pass
