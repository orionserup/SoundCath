import pyvisa as visa # visa for SCPi Commands
import numpy as np # for Various Data and Numerical Operations
from scipy.fft import rfft, rfftfreq # ffts
import csv  # csv for report data
import os   # for mkdir and pwd

scope_sample_interval_ns = 1 # sampling period of oscilloscope

# Oscilloscope Class Wrapper for VISA operations
class Oscilloscope:
    def __init__(self):
        rm = visa.ResourceManager() # create a VISA device manager
        devlist = rm.list_resources()  # print out all of the possible VISA Devices
        print(f"Listing VISA Devices: {devlist}")
        self.Waveform = {"Time": [], "Voltage": []} # a dictionary of Lists
        self.fft = {"Frequency": [], "Amplitude": []}
        self.scope = None # a visa handle for the scope device
        
        for dev in devlist:
            try:
                if not "ASRL" in dev: # if the device is not on the serial port
                    self.scope = rm.open_resource(dev) # open the device for use
                
                if self.scope is not None: # if the scope was found
                    print("Connected To a Scope: {}".format(dev)) # print a status message
                    print("Scope ID: " + self.scope.query("*IDN?"))
                    return                # if we found the scope we are good to leave
            
            except visa.VisaIOError: # if we fun into an error move on to the next device that was found
                self.scope = None
                continue
            
        print("Did Not Find A Valid Scope")  # If we didnt find a 
        self.scope = None

    def IsConnected(self) -> bool: # if we have an active conection to the scope, aka a visa handle
        return self.scope is not None

    def CaptureWaveform(self, channel: int) -> dict[str, list[float]]: # we capture the waveform using standard VISA / SCPI Commands
        
        self.scope.write("HEADER OFF")

        self.scope.write(f"DATa:SOU CH{channel}") # get the waeform from the channel specified in the argument
        self.scope.write("DATa:ENCdg RIBBINARY") # We want the data as binary signed integers
        self.scope.write("DATA WIDTH 1") # we want one byte per point
              
        xinc = float(self.scope.query("WFMOUTPRE:XINCR?")) # we will find what the current x increment is
        ymult = float(self.scope.query('WFMOUTPRE:YMULT?')) # we find out what the y scaling is 
        yoff = float(self.scope.query('WFMOUTPRE:YOFF?')) # we find what the y offset is 
        yzero = float(self.scope.query('WFMOUTPRE:YZERO?')) # we find out where the y zero is at

        self.scope.write("ACQUIRE:STATE OFF")   # stop any waveform capture
        self.scope.write("ACQUIRE:MODE NORMALSAMPLE") # set the capture mode to capture the screen normally like a trigger
        self.scope.write("ACQUIRE:STOPAFTER SEQUENCE")  # set the capture to stop updating the screen after the capture
        
        self.scope.write("ACQUIRE:STATE RUN") # capture the waveform

        while self.scope.query('BUSY?') == '1': # while the waveform is capturing wait for it to finish
            pass

        self.scope.write("DATA:START 1")  # start getting the data from the beginning
        num_samples = int(self.scope.query("HORIZONTAL:RECORD?")) # read how many samples were captured
        self.scope.write("DATA:STOP {}".format(num_samples)) # set the end of the data to the end of the waveform

        values = self.scope.query_binary_values('CURV?', datatype='b') # get the captured waveform

        timeaxis = [i * xinc for i in range(len(values))] # generate a list to represent the time access

        voltage = [ymult * (values[i] - yoff) + yzero for i in range(len(values))] # generate a list of the voltages according to Tektronix this is how a raw V is calculated

        self.Waveform["Time"] = timeaxis # export the data to the class member
        self.Waveform["Voltage"] = voltage

        self.scope.write("ACQUIRE:STOPAFTER RUNSTOP") # set the scope to start capture when a signal is sent
        self.scope.write("ACQUIRE:STATE RUN") # start capture again

        return self.Waveform

    def WindowWaveform(self, initial_us: float = 0.0, window_size_us: float = 5.0) -> dict[str, list]:

        deltat = self.Waveform["Time"][1] - self.Waveform["Time"][0]
        t0 = self.Waveform["Time"][0]

        n = int((initial_us * 1e-6 - t0) / deltat) # we want to start the window as close to the start point as possible
        d = int(window_size_us * 1e-6 / deltat) # we want to make the width of the window as close to the desired width as possible

        if n < 0 or n + d >= len(self.Waveform["Time"]): # if the start is out of the waveform or the windowed waveform extends out of the waveform throw an error
            print("Window Outside of Range")
            return self.Waveform

        self.Waveform = { "Time": self.Waveform["Time"][n: n + d], 'Voltage': self.Waveform["Voltage"][n: n + d] } # window the waveform and time axis
        return self.Waveform

    def GetWaveform(self) -> dict[str, list]:
        return self.Waveform

    def CalculateFFT(self) -> dict[str, list]:

        amp = np.abs(rfft(self.Waveform["Voltage"]))  # run the fft on the voltage values get the magnitude of the amplitude
        freqaxis = rfftfreq(len(self.Waveform["Time"]), self.Waveform["Time"][1] - self.Waveform["Time"][0])  # scale the axis to the sampling period
        
        self.fft["Frequency"] = freqaxis
        self.fft["Amplitude"] = amp

        return self.fft

    def WindowFFT(self, start_freq: float, window_size: float) -> dict[str, list[float]]:

        deltaf = self.fft["Frequency"][1] - self.fft["Frequency"][0] # we want to get the start as close to the desired star as possible
        f0 = self.fft["Frequency"][0]

        n = int((start_freq - f0) / deltaf)
        d = int(window_size / deltaf)

        if n < 0 or n + d >= len(self.fft["Frequency"]):
            print("Window Outside of Range")
            return self.fft

        self.fft = { "Frequency": self.fft["Frequency"][n: n + d], "Amplitude": self.fft["Amplitude"][n: n + d] }
        return self.fft

    def GetFFT(self) -> dict[str, list]:
        return self.fft

    def WriteDataToCSVFile(self, filename: str) -> None:    

        with open(filename + "wave.csv", "w") as wavefile:
            writer = csv.writer(wavefile)
            writer.writerows(zip(self.Waveform["Time"], self.Waveform["Voltage"]))        
                
        with open(filename + "fft.csv", "w") as fftfile:
            writer = csv.writer(fftfile)
            writer.writerows(zip(self.fft["Frequency"], self.fft["Amplitude"]))

# module main function for testing

if __name__ == "__main__":

    import matplotlib.pyplot as plt

    import atexit
    atexit.register(input, "Press Any Key To Continue")

    scope = Oscilloscope()
        
    scope.CaptureWaveform(1) # capture the waveform from the screen
    data = scope.WindowWaveform(4.95, .10)

    minimum = min(data["Voltage"]) # find the minimum voltage of the waveform
    maximum = max(data["Voltage"]) # find the maximum voltage of the waveform
        
    vpp = maximum - minimum # get the peak to peak maximum 

    import matplotlib.pyplot as plt

    fig, plots = plt.subplots(2, 1)        
    plots[0].plot(data["Time"], data["Voltage"], 'b-')
    plots[0].set_xlabel("Time")
    plots[0].set_ylabel("Voltage")

    scope.CalculateFFT() # calculate the fft of the waveform        
    fft = scope.WindowFFT(1e6, 8e6)

    plots[1].plot(fft["Frequency"], fft["Amplitude"], 'r-')
    plots[1].set_xlabel("Frequency")
    plots[1].set_ylabel("Amplitude")    

    fig.tight_layout()
    plt.show(block=False)

    maxamp = np.amax(fft['Amplitude'])
    maxindex = np.where(fft['Amplitude'] == maxamp)

    leftband = fft['Frequency'][maxindex[0][0]]
    rightband = fft['Frequency'][maxindex[0][0]]
        
    for i in range(maxindex[0][0], len(fft['Frequency'])):
        if fft['Amplitude'][i] <= maxamp / 2: # -3db cutoff aka half of the max amplitude
            rightband = fft["Frequency"][i - 1]
            break

    for i in range(maxindex[0][0], 0, -1):
        if fft['Amplitude'][i] <= maxamp / 2:
            leftband = fft["Frequency"][i + 1]
            break

    bandwidth = rightband - leftband

    print(f"Vpp: {vpp} Bandwidth: {bandwidth} Peak Frequency: { (leftband + rightband) / 2 }")



