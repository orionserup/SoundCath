import pyvisa as visa
import csv
import serial
from serial.tools.list_ports import comports
from scipy.fft import rfft, rfftfreq
import numpy as np
import time

scope_sample_interval_ns = 1 # sampling period of oscilloscope

class CatheterTester:
    def __init__(self):
        self.Arduino = Arduino()
        self.Oscilloscope = Oscilloscope()
        self.VNA = VNA()

        """ if not self.Arduino.IsConnected():  # if could not connect to the arduino
            print("Could Not Connect To the Arduino, Exiting")
            input("Press Any Key To Exit")
            exit() # leave the program"""
                
    def ImpedanceTest(self, channel: int, duration: np.double, filename: str) -> bool:
        pass

    def PulseEchoTest(self, channel: int, duration: np.double, filename: str) -> bool:
        pass

    def SetChannel(self, channel: int):
        self.Arduino.Write(channel.to_bytes(1, 'big'))

def WriteDataToFile(self, data: dict[str, list], filename: str) -> None:    
    writer = csv.writer(open(filename, "w"))
    writer.writerow(data.keys())
    for i in len(data.items[0]):
        writer.writerow(data.items()[j][i] for j in range(len(data.keys())))

# Oscilloscope Class Wrapper for VISA operations
class Oscilloscope:
    def __init__(self):
        rm = visa.ResourceManager() # create a VISA device manager
        devlist = rm.list_resources()  # print out all of the possible VISA Devices
        print("Listing VISA Devices: {}".format(devlist))
        self.Waveform = {}
        self.fft = {}
        
        for dev in devlist:
            try:
                self.scope = rm.open_resource(dev) # open the device for use
                self.scope.query("*IDN?")
                
            except visa.VisaIOError:
                self.scope = None
                continue
            
            if self.scope != None:
                print("Connected To a Scope: {}".format(dev))
                print("Scope ID: " + self.scope.query("*IDN?"))
                return

        print("Did Not Find A Valid Scope")

    def IsConnected(self) -> bool:
        return self.scope != None

    def CaptureWaveform(self, channel: int, interval_us: int) -> dict[str, list]:
        self.Oscilloscope.write("HEADER OFF")
        self.Oscilloscope.write("DATa:SOURCe ch{}".format(channel))
        self.Oscilloscope.write("DATa:ENCdg RIBBINARY")
        self.Oscilloscope.write("DATA WIDTH 1")
        self.Oscilloscope.write("ACQUIRE:STATE OFF")
        self.Oscilloscope.write("ACQUIRE:MODE NORMALSAMPLE")
        self.Oscilloscope.write("ACQUIRE:STOPAFTER SEQUENCE")
        self.Oscilloscope.write("ACQUIRE:STATE RUN")
        
        while self.Oscilloscope.query("BUSY?") == "1":
            pass

        num_samples = self.Oscilloscope.query("HORIZONTAL:RECORD?")
        self.Oscilloscope.write("DATA:START 1")
        
        inc = self.Oscilloscope.query("WFMOUTPRE:XINCR?")
        ymult = self.Oscilloscope.query('WFMOUTPRE:YMULT?')
        yoff = self.Oscilloscope.query('WFMOUTPRE:YOFF?')
        yzero = self.Oscilloscope.query('WFMOUTPRE:YZERO?')

        inc_us = np.double(inc) * 1000000
        stop = int(np.double(interval_us)/np.double(inc_us))

        self.Oscilloscope.write("DATA:STOP {}".format(num_samples if stop > num_samples else stop))

        values = self.Oscilloscope.query_binary_values("CURVE?", datatype = "b")
        time = [i * np.double(inc) for i in range(stop)]
        voltage = [np.double(ymult)*(values[i] - np.double(yoff)) - np.double(yzero) for i in range(stop)]

        self.Waveform = {"Time": time, "Voltage": voltage}
        return self.Waveform

    def WindowWaveform(self, initial_us: np.double, window_size_us: np.double) -> dict[str, list]:
        deltat = self.Waveform["Time"][1] - self.Waveform["Time"][0]
        n = int(initial_us/(deltat*1000000))
        d = int(window_size_us/(deltat*1000000))

        self.Waveform = { "Time": self.Waveform["Time"][n: n+d], 'Voltage': self.Waveform["Voltage"][n: n+d] }
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

class Arduino:
    def __init__(self):
        all_ports = comports()
        print("Listing Serial Ports: ")
        ports = set()
        
        for port, _, _ in all_ports: # for every detected port add it to a set of port names
            ports |= {port}
            print(str(port))

        for port in ports:  # for every port in the set try to connect to it
            try:
                dev = serial.Serial(port = port, baudrate = 115200, timeout = .5)

                time.sleep(.1)
                dev.write(bytes("60", 'utf-8'))
                dev.readline()

                dev.write(bytes("32", 'utf-8'))
                ret = dev.readline()

                if ret != b'': # if the echo tests passes return that port
                    print("Connected To Arduino on Port:  " + str(port))
                    self.port = dev
                    return

                else:
                    dev.close()

            except serial.SerialException: # if there is an issue with the port go onto the next one
                continue

        print("Could Not Connect To A Valid Arduino Serial Port") # if we couldn't find a working Arduino then print this message
        self.port = None

    def IsConnected(self) -> bool:
        return self.port != None

    def Write(self, data: bytes) -> int:
        if self.port is not None:
            time.sleep(.1)
            self.port.write(data)
            return len(data)

        return 0

    def Read(self, size: int) -> bytes:
        if self.port is not None:
            return self.port.read(size)

class VNA:
    def __init__(self):
        pass
    