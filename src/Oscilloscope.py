import pyvisa as visa
import numpy as np
from scipy.fft import rfft, rfftfreq
import csv
import os

scope_sample_interval_ns = 1 # sampling period of oscilloscope

# Oscilloscope Class Wrapper for VISA operations
class Oscilloscope:
    def __init__(self):
        rm = visa.ResourceManager() # create a VISA device manager
        devlist = rm.list_resources()  # print out all of the possible VISA Devices
        print(f"Listing VISA Devices: {devlist}")
        self.Waveform = {}
        self.fft = {}
        self.scope = None
        
        for dev in devlist:
            try:
                if not "ASRL" in dev:
                    self.scope = rm.open_resource(dev) # open the device for use
                    self.scope.query("*IDN?")
                
                if self.scope != None:
                    print("Connected To a Scope: {}".format(dev))
                    print("Scope ID: " + self.scope.query("*IDN?"))
                    return                
            
            except visa.VisaIOError:
                self.scope = None
                continue
            
        print("Did Not Find A Valid Scope")
        self.scope = None

    def IsConnected(self) -> bool:
        return self.scope is not None

    def CaptureWaveform(self, channel: int) -> dict[str, list[float]]:
        
        self.scope.write("HEADER OFF")

        self.scope.write(f"DATa:SOU CH{channel}")
        self.scope.write("DATa:ENCdg RIBBINARY")
        self.scope.write("DATA WIDTH 1")        
              
        xinc = float(self.scope.query("WFMOUTPRE:XINCR?"))
        ymult = float(self.scope.query('WFMOUTPRE:YMULT?'))
        yoff = float(self.scope.query('WFMOUTPRE:YOFF?'))
        yzero = float(self.scope.query('WFMOUTPRE:YZERO?'))

        self.scope.write("ACQUIRE:STATE OFF")
        self.scope.write("ACQUIRE:MODE NORMALSAMPLE")
        self.scope.write("ACQUIRE:STOPAFTER SEQUENCE")
        
        self.scope.write("ACQUIRE:STATE RUN")

        while self.scope.query('BUSY?') == '1':
            pass

        self.scope.write("DATA:START 1")  
        num_samples = int(self.scope.query("HORIZONTAL:RECORD?"))
        self.scope.write("DATA:STOP {}".format(num_samples))

        values = self.scope.query_binary_values('CURV?', datatype='b')

        timeaxis = [i * xinc for i in range(len(values))]

        voltage = [ymult * (values[i] - yoff) + yzero for i in range(len(values))]

        self.Waveform["Time"] = timeaxis
        self.Waveform["Voltage"] = voltage

        self.scope.write("ACQUIRE:STOPAFTER RUNSTOP")
        self.scope.write("ACQUIRE:STATE RUN")

        return self.Waveform

    def WindowWaveform(self, initial_us: float = 0.0, window_size_us: float = 5.0) -> dict[str, list]:
        deltat = self.Waveform["Time"][1] - self.Waveform["Time"][0]

        n = int(initial_us * 1e-6/deltat )
        d = int(window_size_us * 1e-6/deltat)

        self.Waveform = { "Time": self.Waveform["Time"][n: n + d], 'Voltage': self.Waveform["Voltage"][n: n + d] }
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

        deltaf = self.fft["Frequency"][1] - self.fft["Frequency"][0]
        f0 = self.fft["Frequency"][0]

        n = int((start_freq - f0) / deltaf)
        d = int(window_size / deltaf)

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



