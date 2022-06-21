import pyvisa as visa
import numpy as np
from scipy.fft import rfft, rfftfreq
import csv
import os

scope_sample_interval_ns = 1 # sampling period of oscilloscope

# Oscilloscope Class Wrapper for VISA operations
class Oscilloscope:
    def __init__(self):
        rm = visa.ResourceManager('@py') # create a VISA device manager
        devlist = rm.list_resources()  # print out all of the possible VISA Devices
        print(f"Listing VISA Devices: {devlist}")
        self.Waveform = None
        self.fft = None
        self.scope = None

        devs = list(devlist)
        devs.append("USB0::0x0699::0x0378::C001088::INSTR")
        
        for dev in devs:
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

    def CaptureWaveform(self, channel: int, interval_us: int) -> dict[str, list]:
        
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

        num_samples = self.scope.query("HORIZONTAL:RECORD?")
        self.scope.write("DATA:START 1")
        
        inc = self.scope.query("WFMOUTPRE:XINCR?")
        ymult = self.scope.query('WFMOUTPRE:YMULT?')
        yoff = self.scope.query('WFMOUTPRE:YOFF?')
        yzero = self.scope.query('WFMOUTPRE:YZERO?')

        inc_us = np.double(inc) * 1000000
        stop = int(np.double(interval_us)/np.double(inc_us))

        self.scope.write("DATA:STOP {}".format(num_samples if stop > num_samples else stop))

        values = self.scope.query_binary_values("CURVE?", datatype = "b")
        time = [i * np.double(inc) for i in range(stop)]
        voltage = [np.double(ymult)*(values[i] - np.double(yoff)) - np.double(yzero) for i in range(stop)]

        self.Waveform = {"Time": time, "Voltage": voltage}
        return self.Waveform

    def WindowWaveform(self, initial_us: np.double = 0.0, window_size_us: np.double = 5.0) -> dict[str, list]:
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
        if self.fft is not None:
            writer = csv.writer(open(filename + "fft.csv", "w"))
            for i in len(self.fft["Frequency"]):
                writer.writerow([self.fft["Frequency"][i], self.fft["Amplitude"][i]])

        if self.Waveform is not None:
            writer = csv.writer(open(filename + "wave.csv", "w"))
            for i in len(self.fft["Time"]):
                writer.writerow([self.fft["Time"][i], self.fft["Voltage"][i]])

# module main function for testing

if __name__== "__main__":

    import matplotlib.pyplot as plt

    import atexit
    atexit.register(input, "Press Any Key To Continue")

    scope = Oscilloscope()
    if(scope.IsConnected()):
        scope.CaptureWaveform(1, 8)
        scope.WindowWaveform(0, 6.0)
        wave = scope.GetWaveform()
        plt.subplot(1, 2, 1)
        plt.plot(wave["Voltage"], wave["Time"])
        plt.subplot(1, 2, 2)
        fft = scope.CalculateFFT()
        plt.plot(fft["Amplitude"], fft["Frequency"])
        plt.show()

        scope.WriteDataToCSVFile()


