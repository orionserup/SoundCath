
import os
import glob
import csv

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
        self.parameters = [ "s11"]
        self.executable = "C:\\VNWA\\VNWA.exe"
        self.scriptfile = os.getcwd() + "\\Script.scr"
        self.calsweep = None
        self.calsweepverbose = False
        self.path = os.getcwd()
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
        self.file = filename

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

            if len(self.parameters) != 0:
                file.write("sweep ")
                for param in self.parameters:
                    file.write(param + " ")

                file.write("\n")
            
                for param in self.parameters:
                    file.write(f"writes1p {self.path + self.file + param}.s1p {param}\n")
            
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
        data["Frequency"].append(datem[0])
        data["Real"].append(datem[1])
        data["Imaginary"].append(datem[2])

    csvwriter = csv.writer(csvfile)
    for i in range(len(data["freq"])):
        csvwriter.writerow( [ data["Frequency"][i], data["Real"][i], data["Imaginary"][i]])

    csvfile.close()
    s1pfile.close()

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