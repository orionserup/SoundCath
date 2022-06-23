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
        self.Waveform = None
        self.fft = None
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
        return self.scope != None

    def CaptureWaveform(self, channel: int) -> dict[str, list]:
        
        self.scope.write("HEADER OFF")
        self.scope.write(f"DATa:SOURCe ch{channel}")
        self.scope.write("DATa:ENCdg RIBBINARY")
        self.scope.write("DATA WIDTH 1")
        self.scope.write("ACQUIRE:STATE OFF")
        self.scope.write("ACQUIRE:MODE NORMALSAMPLE")
        self.scope.write("ACQUIRE:STOPAFTER SEQUENCE")
        self.scope.write("ACQUIRE:STATE RUN")
        
        while self.scope.query("BUSY?") == "1":
            pass

        num_samples = int(self.scope.query("HORIZONTAL:RECORD?"))
        self.scope.write("DATA:START 1")
        
        inc = float(self.scope.query("WFMOUTPRE:XINCR?"))
        ymult = float(self.scope.query('WFMOUTPRE:YMULT?'))
        yoff = float(self.scope.query('WFMOUTPRE:YOFF?'))
        yzero = float(self.scope.query('WFMOUTPRE:YZERO?'))

        self.scope.write("DATA:STOP {}".format(num_samples))

        values = self.scope.query_binary_values("CURVE?", datatype = "b")

        timeaxis = [ float(i * inc) for i in range(len(values))]
        voltage = [float(ymult * (values[i] - yoff) - yzero) for i in range(len(values))]

        self.Waveform["Time"] = timeaxis
        self.Waveform["Voltage"] = voltage

        return self.Waveform

    def WindowWaveform(self, initial_us: np.double = 0.0, window_size_us: float = 5.0) -> dict[str, list]:
        deltat = self.Waveform["Time"][1] - self.Waveform["Time"][0]

        n = int(initial_us/(deltat*1000000))
        d = int(window_size_us/(deltat*1000000))

        self.Waveform = { "Time": self.Waveform["Time"][n: n + d], 'Voltage': self.Waveform["Voltage"][n: n + d] }
        return self.Waveform

    def GetWaveform(self) -> dict[str, list]:
        return self.Waveform

    def CalculateFFT(self) -> dict[str, list]:

        amp = np.abs(rfft(self.Waveform["Voltage"]))  # run the fft on the voltage values get the magnitude of the amplitude
        freq = rfftfreq(len(self.Waveform["Time"]), self.Waveform["Time"][1]- self.Waveform["Time"][0])  # scale the axis to the sampling period
        
        self.fft = {"Frequency": freq, "Amplitude": amp}
        return self.fft

    def GetFFT(self) -> dict[str, list]:
        return self.fft

    def WriteDataToCSVFile(self, filename: str) -> None:    
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        if self.Waveform is not None:
            writer = csv.writer(open(filename + "wave.csv", "w"))
            for i in len(self.Waveform["Time"]):
                writer.writerow([self.fft["Time"][i], self.fft["Voltage"][i]])        
                
        if self.fft is not None:
            writer = csv.writer(open(filename + "fft.csv", "w"))
            for i in len(self.fft["Frequency"]):
                writer.writerow([self.fft["Frequency"][i], self.fft["Amplitude"][i]])

# module main function for testing

if __name__== "__main__":

    import matplotlib.pyplot as plt

    import atexit
    atexit.register(input, "Press Any Key To Continue")

    scope = Oscilloscope()
    data = []
    if(scope.IsConnected()):
        scope.CaptureWaveform(1)
        data = scope.WindowWaveform(0, 9.0)
        
    minimum = min(data["Voltage"]) # find the minimum voltage of the waveform
    maximum = max(data["Voltage"]) # find the maximum voltage of the waveform
        
    vpp = maximum - minimum # get the peak to peak maximum 

    import matplotlib.pyplot as plt

    waveplot = plt.subplot(1, 2, 1)
    waveplot.plot(data["Time"], data["Voltage"], 'b.')
    waveplot.set_title("Waveform")

    fft = scope.CalculateFFT() # calculate the fft of the waveform        
        
    fftplot = plt.subplot(1, 2, 2)
    fftplot.plot(fft["Frequency"], fft["Amplitude"], 'r.')
    fftplot.set_title("FFT")

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

    print(f"Vpp: {vpp} Bandwidth: {bandwidth}")

    scope.WriteDataToCSVFile("test")


