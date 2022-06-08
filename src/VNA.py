
import os
import glob
import csv

inputimpedance = 50

class VNA:
    def __init__(self):
        self.lowfreq = 1000000 # the frequency to start at
        self.highfreq = 1300000000 # the frequency to end at
        self.mastercal = None # master calibration file
        self.calfile = None # "C:\\VNWA\\VNWA.cal" # Calibration File Path
        self.numpoints = 2000 # The Number of Points to Test Between the Frequencies
        self.scale = "lin" # [lin / log]
        self.timeperpoint = 10 # How Long to wait before capturing the value
        self.txpower = 4000 # how much power to test with
        self.parameters = ["s11"] # which parameters to test with [s11, s22, s12, s21]
        self.executable = "C:\\VNWA\\VNWA.exe" # The Path of the VNA Utility 
        self.scriptfile = "Script.scr" # the Name of the Script File
        self.calsweep = None # How to Run the Calibration Sweep [ Open Short Crosstalk Thru] None for Dont 
        self.calsweepverbose = False # if we are doing a verbose Calibration Sweep
        self.filename = "Test" # Name to Save the File As, only the root of it
        
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

    def SetScale(self, scale: str = "log"):
        self.scale = scale

    def SetSweepParameters(self, params: list[str] = [ "s11"]):
        self.parameters = params

    def SetNumPoints(self, points: int):
        self.numpoints = points

    # Writes and Executes a Script File According to the Class Parameters
    def Sweep(self):
        with open(self.scriptfile, "w") as file: # open the Script for writing
            
            # see VNWA Handbook 

            if self.mastercal is not None: # if we are using a master calibration load it
                file.write(f"loadmastercal {self.mastercal}\n")

            if self.calfile is not None: # if we are using a Calibration File Load it
                file.write(f"loadcal {self.calfile}\n")

            if self.calsweep is not None: # If we are Running a Calibration Sweep Set it
                file.write(f"calsweep {self.calsweep}")
                file.write( "nv\n" if not self.calsweepverbose else "\n")

            file.write(f"range {self.lowfreq} {self.highfreq}\n") # Set the Start Frequency and Stop Frequency
            file.write(f"frame {self.numpoints} {self.scale}\n") # Set the Scale and Number of Points
            file.write(f"timeperpoint {self.timeperpoint}\n") # Set the Time Per Point
            file.write(f"setTXpower {self.txpower}\n") # Set the Transmission Power for Measurement                


            if len(self.parameters) != 0: # for all of the parameters to measure            
                
                file.write("sweep ") 
                for param in self.parameters:
                    file.write(param + " ") # sweep over that range and measure the parameter

                file.write("\n")                
                
                for param in self.parameters: # for each of the meausured parameters write the data to a file
                    file.write(f"writes1p { self.filename + param}.s1p {param}\n")
            
            file.write("exitVNWA \n") # leave the VNA app so you can do this again

        os.system("{} {} -debug".format(self.executable, self.scriptfile)) # Run this Script File Through the VNA App

# Takes an S1P File Parses it, grabs the data and Writes the Data to a CS File
def ConvertS1PToCSV(filename: str) -> dict[str, complex]:

    csvfile = open(filename.replace("s1p", "csv"), "w") # open the csv file for writing
    s1pfile = open(filename, "r") #read the s1p file

    # read the s1p file according to the touchstone specifications
    s1pfile.readline()
    s1pfile.readline()

    # Setup an empty Dictionary To Hold the S1P Values
    data = {"Frequency": [], "Value": [], "Z": []}

    # line for line extract the data
    for line in s1pfile:
        items = line.split("   ")
        datem = [float(item) for item in items]

        data["Frequency"].append(1000000 * datem[0]) # Frequency in units of MHz
        
        real = datem[1]
        imag = datem[2]
        data["Value"].append(complex(real, imag)) # scale is in MHz

    # if we read s11 data we can get the impedance
    if "s11" in filename: 
        # open a file for writing the impedance values to
        zcsvfile = open(filename.replace("s1p", "csv").replace("s11", "z"), 'w')
        zcsvwriter = csv.writer(zcsvfile)

        for (i, val) in enumerate(data["Value"]): # calculate the impedance for every frequency
            data["Z"].append(inputimpedance * (1 + val)/(1 - val))
            zcsvwriter.writerow([ data["Frequency"][i], data["Z"][i] ]) # Write the Frequency and Impedance for every value to a CSV File
            
        zcsvfile.close() # Write the File to the System

    # Create A CSV File and Write All of the Data To it
    csvwriter = csv.writer(csvfile)
    for i in range(len(data["Frequency"])):
        csvwriter.writerow( [ data["Frequency"][i], data["Value"][i] ])

    csvfile.close()
    s1pfile.close()
    
    return data


if __name__ == "__main__":

    import atexit
    atexit.register(input, "Press Any Key To Continue")
    
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