
import pyvisa as visa
import glob
import csv
import serial
from serial.tools.list_ports import comports
from scipy.fft import rfft, rfftfreq
import numpy as np
import time
import os

scope_sample_interval_ns = 1 # sampling period of oscilloscope

class CatheterTester:
    def __init__(self):
        self.Arduino = Arduino()
        self.Oscilloscope = Oscilloscope()
        self.VNA = VNA()

        if not self.Arduino.IsConnected():  # if could not connect to the arduino
            print("Could Not Connect To the Arduino, Exiting")
            input("Press Any Key To Exit")
            exit() # leave the program
                
    def ImpedanceTest(self, channel: int, duration: np.double, filename: str) -> bool:
        pass

    def PulseEchoTest(self, channel: int = 1, duration_us: np.double = 6, filename: str = "cath.csv") -> bool:
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
        rm = visa.ResourceManager('@py') # create a VISA device manager
        devlist = rm.list_resources()  # print out all of the possible VISA Devices
        print(f"Listing VISA Devices: {devlist}")
        self.Waveform = {}
        self.fft = {}
        
        for dev in devlist:
            try:
                self.scope = rm.open_resource(dev) # open the device for use
                self.scope.query("*IDN?")
                
                if self.scope != None:
                    print("Connected To a Scope: {}".format(dev))
                    print("Scope ID: " + self.scope.query("*IDN?"))
                    return                
            
            except visa.VisaIOError:
                self.scope = None
                continue

            except serial.SerialException:
                self.scope = None
                continue
            
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

class Arduino:
    def __init__(self):
        all_ports = comports()
        print("Listing Serial Ports: ")
        
        for port, info, _ in all_ports: # for every detected port add it to a set of port names
            print(str(info))

            if "Arduino" in str(info):
                self.port = serial.Serial(port, baudrate = 115200, timeout = .5)
                print(f"Connected to Arduino on Port {port}\n")
                return

        print("Could Not Connect To A Valid Arduino Serial Port") # if we couldn't find a working Arduino then print this message
        self.port = None

    def IsConnected(self) -> bool:
        return self.port != None

    def Write(self, data: bytes) -> int:
        if self.port is not None:
            time.sleep(.01)
            self.port.write(data)
            return len(data)

        return 0

    def Read(self, size: int) -> bytes:
        if self.port is not None:
            return self.port.read(size)

    def ReadLine(self) -> bytes:
        if self.port is not None:
            return self.port.readline()

class VNA:
    def __init__(self):
        self.lowfreq = 1000000
        self.highfreq = 100000000
        self.mastercal = None
        self.calfile = "C:\\VNWA\\VNWA.cal"
        self.numpoints = 400
        self.scale = "log"
        self.timeperpoint = 10
        self.txpower = 4000
        self.parameters = [ "s11", "s12" ]
        self.executable = "C:\\VNWA\\VNWA.exe"
        self.scriptfile = os.getcwd() + "\\Script.scr"
        self.calsweep = None
        self.calsweepverbose = False
        self.path = "..\\data\\"
        
    def SetStartFreq(self, freq: int):
        self.lowfreq = freq

    def SetCalibrationDirection(self, dir: str = None):
        self.caldirection = dir

    def SetCalibrationSweep(self, type, verbose: bool):
        self.calsweep = type
        self.calsweepverbose = verbose
    
    def SetMasterCal(self, filename: str = None):
        self.mastercal = filename

    def SetTimePerPoint(self, tpp: int):
        self.timeperpoint = tpp

    def SetStopFreq(self, freq: int):
        self.highfreq = freq

    def AddSweepParameter(self, source: str):
        self.parameters.append(source)

    def SetScale(self, scale: str = "Log"):
        self.scale = scale

    def SetSweepParameters(self, params: list[str] = [ "s11", "s12"]):
        self.parameters = params

    def SetNumPoints(self, points: int):
        self.numpoints = points

    def Sweep(self):
        with open(self.scriptfile, "w") as file:

            if self.mastercal != None:
                file.write(f"loadmastercal {self.mastercal}\n")

            if self.calfile != None:
                file.write(f"loadcal {self.calfile}\n")

            if self.calsweep != None:
                file.write(f"calsweep {self.calsweep}")
                file.write( "nv\n" if not self.calsweepverbose else "\n")

            file.write(f"range {self.lowfreq} {self.highfreq}\n")
            file.write(f"frame {self.numpoints} {self.scale}\n")
            file.write(f"timeperpoint {self.timeperpoint}\n")
            file.write(f"setTXpower {self.txpower}\n")

            file.write("sweep ")
            for param in self.parameters:
                file.write(param + " ")
            
            file.write("\n")

            for param in self.parameters:
                file.write(f"writes1p {self.path + param}.s1p {param}\n")
        
            file.write("exitVNWA")

        os.system("{} {} -debug".format(self.executable, self.scriptfile))

def ConvertS1PToCSV(filename: str):
    csvfile = open(filename.replace("s1p", "csv"), "w")
    s1pfile = open(filename, "r")

    s1pfile.readline()
    s1pfile.readline()

    data = {"freq": [], "mag": [], "phase": []}

    for line in s1pfile:
        items = line.split("   ")
        datem = [float(item) for item in items]
        data["freq"].append(datem[0])
        data["mag"].append(datem[1])
        data["phase"].append(datem[2])

    csvwriter = csv.writer(csvfile)
    for i in range(len(data["freq"])):
        csvwriter.writerow( [ data["freq"][i], data["mag"][i], data["phase"][i]])

    csvfile.close()
    s1pfile.close()

if __name__ == "__main__":
    
    vna = VNA()
    vna.AddSweepParameter("s22")
    vna.SetCalibrationSweep("Open", True)
    vna.Sweep()

    files = glob.glob("..\\data\\*.s1p")
    for f in files:
        ConvertS1PToCSV(f)

