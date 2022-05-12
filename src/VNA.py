
from multiprocessing.sharedctypes import Value
import os
import glob
import csv
import cmath

inputimpedance = 50

class VNA:
    def __init__(self):
        self.lowfreq = 1000000
        self.highfreq = 1300000000
        self.mastercal = None
        self.calfile = "C:\\VNWA\\VNWA.cal"
        self.numpoints = 2000
        self.scale = "log"
        self.timeperpoint = 10
        self.txpower = 4000
        self.parameters = ["s11"]
        self.executable = "C:\\VNWA\\VNWA.exe"
        self.scriptfile = os.getcwd() + "\\Script.scr"
        self.calsweep = None
        self.calsweepverbose = False
        self.filename = ""
        
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

    def SetFileName(self, filename: str) -> None:
        self.filename = filename

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

            if self.mastercal is not None:
                file.write(f"loadmastercal {self.mastercal}\n")

            if self.calfile is not None:
                file.write(f"loadcal {self.calfile}\n")

            if self.calsweep is not None:
                file.write(f"calsweep {self.calsweep}")
                file.write( "nv\n" if not self.calsweepverbose else "\n")

            file.write(f"range {self.lowfreq} {self.highfreq}\n")
            file.write(f"frame {self.numpoints} {self.scale}\n")
            file.write(f"timeperpoint {self.timeperpoint}\n")
            file.write(f"setTXpower {self.txpower}\n")

            if len(self.parameters) != 0:
                file.write("sweep ")
                for param in self.parameters:
                    file.write(param + " ")

                file.write("\n")
            
                for param in self.parameters:
                    file.write(f"writes1p {self.filename + param}.s1p {param}\n")
            
            #file.write("exitVNWA \n")

        os.system("{} {} -debug".format(self.executable, self.scriptfile))

def ConvertS1PToCSV(filename: str) -> dict[str, complex]:

    csvfile = open(filename.replace("s1p", "csv"), "w")
    s1pfile = open(filename, "r")

    s1pfile.readline()
    s1pfile.readline()

    data = {"Frequency": [], "Value": []}

    for line in s1pfile:
        items = line.split("   ")
        datem = [float(item) for item in items]
        data["Frequency"].append(datem[0])
        real = datem[1]
        imag = datem[2]
        data["Value"].append(complex(real, imag))

    if "s11" in filename: 
        zcsvfile = open(filename.replace("s1p", "csv").replace("s11", "z"))
        zcsvwriter = csv.writer(zcsvfile)

        for (i, val) in enumerate(data["Value"]):
            data["Z"][i] = inputimpedance * (1 + val)/(1 - val)
            zcsvwriter.writerow([ data["Frequency"][i], data["Z"][i] ])
            
        zcsvfile.close()

    csvwriter = csv.writer(csvfile)
    for i in range(len(data["Frequency"])):
        csvwriter.writerow( [ data["Frequency"][i], data["Value"][i] ])

    csvfile.close()
    s1pfile.close()
    
    return data


if __name__ == "__main__":
    
    vna = VNA()
    vna.SetTimePerPoint(10)
    vna.SetNumPoints(500)
    vna.SetStartFreq(100000)
    vna.SetStopFreq(100000000)
    vna.SetScale("Log")
    vna.SetSweepParameters(['s11'])
    #vna.AddSweepParameter("s22")
    #vna.SetCalibrationSweep("Open", True)

    vna.Sweep()

    files = glob.glob("./*.s1p")
    for f in files:
        ConvertS1PToCSV(f)