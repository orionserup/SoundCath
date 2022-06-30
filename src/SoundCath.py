from fileinput import filename
from tkinter import StringVar, ttk, Tk, IntVar, Toplevel
import time
import TesterBackend as tb
import csv
import os

vnachanneloffset = 1 << 7
scopechanneloffset = 1 << 6

class TesterFrontEnd:  # a GUI front end for the test

    def __init__(self):
        # Configure the GUI Basic Parts
        self.root = Tk() # setup the GUI base
        self.root.title("Catheter Tester Script")
        self.root.geometry("600x400")

        self.style = ttk.Style()
        self.style.configure("TCheckbutton", font = ("Arial", 16))
        self.style.configure("TButton", font = ("Arial", 18))
        self.style.configure("TEntry", font = ("Arial", 24))
        self.style.configure("TLabel", font = ("Arial", 18))

        # All of the Internal Variables
        self.channel = 0 # the channel we are in
        self.impedancetest = IntVar(self.root, 0) # bool for if we are gonna run the impedance test
        self.allchannels = IntVar(self.root, 0) # bool if we are gonna test all channels
        self.pulseechotest = IntVar(self.root, 0) # bool if we are gonna run the pulse echo test
        self.dongletest = IntVar(self.root, 0) # bool if we are gonna run a dongle test
        self.text = StringVar(self.root, "Channel " + str(self.channel)) # the string to display the channel

        # Variable to Store the Results of all of the Tests
        self.passmap = { "Impedance": [False, None] * tb.max_channel, "PulseEcho": [False, None, None, None] * tb.max_channel, "Dongle": [False, None] * tb.max_channel}
        self.backend = tb.CatheterTester() # Backend tester that does the actual work 

        self.window = ttk.Frame(self.root)  # All widget elements
        
        self.upbutton = ttk.Button(self.root, text = "Up", command = self.IncChannel) # the up button
        self.downbutton = ttk.Button(self.root, text = "Down", command = self.DecChannel) # the down button
        
        self.label = ttk.Label(self.root, textvariable = self.text, width = 11) # Label to draw the Channel Number
        self.filenamelabel = ttk.Label(self.root, text = "File Name to Save:") # Entry box to put the filename into
        self.filename = ttk.Entry(self.root)

        self.impedancetestbutton = ttk.Checkbutton(self.root, variable = self.impedancetest, text = "Impedance Test") # all of the check boxes
        self.allchannelsbutton  = ttk.Checkbutton(self.root, variable = self.allchannels,  text = "Run All Channels")
        self.pulseechotestbutton = ttk.Checkbutton(self.root, variable = self.pulseechotest, text = "Pulse Echo")
        self.dongletestbutton = ttk.Checkbutton(self.root, variable = self.dongletest, text = "Dongle Test")

        self.runbutton = ttk.Button(self.root, text = "Run Tests", command = self.RunTests) # all of the buttons to actually run the tests and get results and stuff
        self.results = ttk.Button(self.root, text = "Results", command = self.DisplayPassMap )
        self.reportbutton = ttk.Button(self.root, text = "Generate Report", command = self.GenerateReport)

    def Draw(self) -> None: # positions and draws all of the widgets in the frame

        self.upbutton.place(x = 400, y = 50)
        self.label.place(x = 240 , y = 50)
        self.downbutton.place(x = 50, y = 50)

        self.impedancetestbutton.place(x = 50, y = 100)
        self.pulseechotestbutton.place(x = 250, y = 100)
        self.allchannelsbutton.place(x = 400, y = 100)
        self.dongletestbutton.place(x = 50, y = 150)

        self.reportbutton.place(x = 50, y = 300)
        self.runbutton.place(x = 400, y = 300)
        self.results.place(x = 240, y = 300)
        self.filenamelabel.place(x = 50, y = 200)
        self.filename.place(x = 300, y = 200, height = 50, width = 250)

        self.window.mainloop()
        
    # Draws a Small Window with One button to trigger the  
    def TriggerWindow(self) -> None:
        window = Tk()

        button = ttk.Button(window, text = "Capture", command = window.destroy)
        button.pack()
        window.mainloop()

        
    # Displays the List of the tests results for all tests
    def DisplayPassMap(self) -> None:

        Window = Tk()
        ImpedanceLabel = ttk.Label(Window, style = "TLabel",text = f"Impendance Test Results: {self.passmap['Impedance']}")
        PulseEchoLabel = ttk.Label(Window, style = "TLabel",  text = f"Pulse Echo Test Results: {self.passmap['PulseEcho']}")
        DongleLabel = ttk.Label(Window, style = "TLabel", text = f"Dongle Test Results: {self.passmap['Dongle']}")
        Button = ttk.Button(Window, text = "Ok", command = Window.destroy)

        DongleLabel.pack()
        PulseEchoLabel.pack()
        ImpedanceLabel.pack()
        Button.pack()
        Window.mainloop()
            
     
    def RunSingleChannelTest(self, channel, filename) -> None:

        channel = self.channel
        if(self.impedancetest.get() != 0 or self.dongletest.get() != 0 or self.pulseechotest.get() != 0): # repeat the same process with the impedance test/dongle test
            channel &= ~vnachanneloffset
        else:
            channel |= vnachanneloffset

        self.backend.SetChannel(channel - 1);
    
        if self.pulseechotest.get() != 0:
            self.TriggerWindow()
            self.passmap["PulseEcho"][self.channel - 1] = self.RunPulseEchoTest(filename) # Run the Tests and record the Results

        if self.impedancetest.get() != 0:
            self.passmap["Impedance"][self.channel - 1] = self.RunImpedanceTest(filename) 

        if self.dongletest.get() != 0:
            self.passmap["Dongle"][self.channel - 1] =  self.RunDongleTest(filename) 


    def RunTests(self) -> None: # run the tests according to the parameters
        
        filename = os.getcwd() + '\\' + self.filename.get() 
        path = "\\".join(filename.split("\\")[0:-1]) # create the path of the file if it wasn't already there

        os.makedirs(path, exist_ok=True)
        
        if self.allchannels.get() != 0:
            for i in range(tb.max_channel):
                self.RunSingleChannelTest(i, filename)
            
            self.GenerateReport()

        else:
            self.RunSingleChannelTest(self.channel, filename)

    def RunImpedanceTest(self, filename) -> tuple[bool, float, float, float]:
        return self.backend.ImpedanceTest(filename) # run the test with the filename

    def RunPulseEchoTest(self, filename) -> tuple[bool, float]:    
        return self.backend.PulseEchoTest(1, filename) # run the test on scope channel 1 with file name filename
        
    def RunDongleTest(self, filename) -> tuple[bool, float]:
        return self.backend.DongleTest(filename) # Run the Dongle test with the Filename as its file name

    def IncChannel(self) -> None: # increments the channel and displays the change
        if(self.channel < tb.max_channel):
            self.channel += 1
            self.text.set("Channel " + str(self.channel))
            self.backend.SetChannel(self.channel - 1)
            print(self.backend.arduino.ReadLine())

    def DecChannel(self) -> None: # Decrements the channel and display the change
        if(self.channel > 0):
            self.channel -= 1
            self.text.set("Channel " + str(self.channel))
            self.backend.SetChannel(self.channel - 1)
            print(self.backend.arduino.ReadLine())
            
    def GenerateReport(self) -> None: # Generates a CSV Report with all of the results

        filename = os.getcwd() + '\\' + self.filename.get() 

        with open(filename + 'PEReport.csv', 'w') as pefile:
            pewriter = csv.writer(pefile)
            
            pewriter.writerow(["Channel", "Passed", "Vpp", "Bandwidth", "Center Frequency"])
            pewriter.writerows(zip(range(1, len(self.passmap["PulseEcho"]) + 1), self.passmap["PulseEcho"]) )

        with open(filename + 'ZReport.csv', 'w') as zfile:
            zwriter = csv.writer(zfile)
            
            zwriter.writerow(["Channel", "Capacitance"])
            zwriter.writerows(zip(range(1, len(self.passmap["Impedance"]) + 1), self.passmap["Impedance"]) )
        
        with open(filename + "DongleReport", 'w') as donglefile:
            donglewriter = csv.writer(donglefile)
            
            donglewriter.writerow(["Channel", "Capacitance"])
            donglewriter.writerows(zip(range(1, len(self.passmap["Dongle"]) + 1), self.passmap["Dongle"]))
            

if __name__ == "__main__":

    import atexit
    atexit.register(input, "Press Any Key To Continue")

    gui = TesterFrontEnd()
    gui.Draw()

    
    
