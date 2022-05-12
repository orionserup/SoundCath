from tkinter import StringVar, ttk, Tk, IntVar
import time
import TesterBackend as tb
import csv
import os

channel_switch_interval = 3 # when running all channels the time between channels

dongle_thresh = 103e-12
dongle_freq = 800e3

channel_thresh = 100e-12
channel_freq = 500e3

max_channel = 64

vnachanneloffset = 1 << 6
scopechanneloffset = 1 << 7
class TesterFrontEnd:  # a GUI front end for the test
    def __init__(self):
        self.root = Tk() # setup the GUI base
        self.root.title("Catheter Tester Script")
        self.root.geometry("600x400")
        self.style = ttk.Style()
        self.style.configure("TCheckbutton", font = ("Arial", 16))
        self.style.configure("TButton", font = ("Arial", 18))
        self.style.configure("TEntry", font = ("Arial", 24))
        self.style.configure("TLabel", font = ("Arial", 18))

        self.channel = 0
        self.impedancetest = IntVar(self.root, 0) # all private variables
        self.allchannels = IntVar(self.root, 0)
        self.pulseechotest = IntVar(self.root, 0)
        self.dongletest = IntVar(self.root, 0)
        self.text = StringVar(self.root, "Channel " + str(self.channel))

        self.passmap = { "Impedance": [None] * max_channel, "PulseEcho": [None] * max_channel, "Dongle": [None] * max_channel }
        self.backend = tb.CatheterTester()

        self.window = ttk.Frame(self.root)  # All widget elements
        self.upbutton = ttk.Button(self.root, text = "Up", command = self.IncChannel)
        self.downbutton = ttk.Button(self.root, text = "Down", command = self.DecChannel)
        self.label = ttk.Label(self.root, textvariable = self.text, width = 11)
        self.filenamelabel = ttk.Label(self.root, text = "File Name to Save:")

        self.impedancetestbutton = ttk.Checkbutton(self.root, variable = self.impedancetest, text = "Impedance Test")
        self.allchannelsbutton  = ttk.Checkbutton(self.root, variable = self.allchannels,  text = "Run All Channels")
        self.pulseechotestbutton = ttk.Checkbutton(self.root, variable = self.pulseechotest, text = "Pulse Echo")
        self.dongletestbutton = ttk.Checkbutton(self.root, variable = self.dongletest, text = "Dongle Test")

        self.runbutton = ttk.Button(self.root, text = "Run Tests", command = self.RunTests)
        self.results = ttk.Button(self.root, text = "Results", command = self.DisplayPassMap )
        self.filename = ttk.Entry(self.root, text = "File Name")
        self.reportbutton = ttk.Button(self.root, text = "Generate Report", command = self.GenerateReport)

    def Draw(self): # positions and draws all of the widgets in the frame
        self.upbutton.place(x = 400, y = 50)
        self.label.place(x = 240 , y = 50)
        self.downbutton.place(x = 50, y = 50)

        self.impedancetestbutton.place(x = 50, y = 100)
        self.pulseechotestbutton.place(x = 250, y = 100)
        self.allchannelsbutton.place(x = 400, y = 100)
        self.dongletestbutton.place(x = 50, y = 150)

        self.reportbutton.place(x = 50, y = 300)
        self.runbutton.place(x = 400, y = 300)
        self.results.place(x = 250, y = 300)
        self.filenamelabel.place(x = 50, y = 200)
        self.filename.place(x = 300, y = 200, height = 50, width = 250)

        self.window.mainloop()
        

    def DisplayPassWindow(self) -> None:
        PassWindow = Tk()
        PassWindow.geometry('100x200')

        def Pass():
            self.passmap[self.channel] = "Pass"
            PassWindow.destroy()

        def Fail():
            self.passmap[self.channel] = "Fail"
            PassWindow.destroy()

        passbutton = ttk.Button(PassWindow, text = "Pass", command = Pass)
        failbutton = ttk.Button(PassWindow, text = "Fail", command = Fail)
        passbutton.place(x = 0, y = 0, height = 100, width = 100)
        failbutton.place(x = 0, y = 100, height = 100, width = 100)

        PassWindow.mainloop()

    def DisplayPassMap(self) -> None:
        Window = Tk()
        ImpedanceLabel = ttk.Label(Window, style = "TLabel",text = f"Impendance Test Results: {self.passmap['Impedance']}")
        PulseEchoLabel = ttk.Label(Window, style = "TLabel",  text = f"Pulse Echo Test Results: {self.passmap['PulseEcho']}")
        DongleLabel = ttk.Label(Window, style = "TLabel", text = f"Dongle Test Results: {self.passmap['Dongle']}")
        Button = ttk.Button(Window, text = "Ok", command = lambda: Window.destroy())

        DongleLabel.pack()
        PulseEchoLabel.pack()
        ImpedanceLabel.pack()
        Button.pack()
        Window.mainloop()

    def RunAllChannelTests(self):

        channel = self.channel
        if(self.pulseechotest.get() != 0):
            channel |= scopechanneloffset;
        else:
            channel &= ~scopechanneloffset;

        if(self.impedancetest.get() != 0):
            channel |= vnachanneloffset
        else:
            channel &= ~vnachanneloffset

        for i in range(max_channel):
        
            if self.pulseechotest.get():
                self.passmap["PulseEcho"][i] = "Pass" if self.RunPulseEchoTest(i) else "Fail"
   
            if self.impedancetest.get():
                self.passmap["Impedance"][i] = "Pass" if self.RunImpedanceTest(i) else "Fail"
  
            if self.dongletest.get() != 0:
                self.passmap["Dongle"][i] = "Pass" if self.RunDongleTest(i) else "Fail"

            time.sleep(channel_switch_interval)
            
     
    def RunSingleChannelTest(self, channel):

        if(self.pulseechotest.get() != 0):
            channel |= scopechanneloffset;
        else:
            channel &= ~scopechanneloffset;

        if(self.impedancetest.get() != 0):
            channel |= vnachanneloffset
        else:
            channel &= ~vnachanneloffset

        self.backend.SetChannel(channel - 1);

        if self.pulseechotest.get() != 0:
            self.RunPulseEchoTest()
        if self.impedancetest.get() != 0:
            self.RunImpedanceTest()

        self.DisplayPassWindow()
        channel &= ~scopechanneloffset;
        channel &= ~vnachanneloffset
        self.backend.SetChannel(channel)

    def RunTests(self): # run the tests according to the parameters
        
        if self.allchannels.get() != 0:
            self.RunAllChannelTests()

        else:
            self.RunSingleChannelTest(self.channel)

    def RunImpedanceTest(self, channel: int) -> bool:
        filename = "example" if self.filename.get() == "" else self.filename.get() 
        return self.backend.ImpedanceTest(channel, channel_freq, channel_thresh, filename)

    def RunPulseEchoTest(self, channel: int) -> bool:    
        filename = "example" if self.filename.get() == "" else self.filename.get() 
        return self.backend.PulseEchoTest(channel, 9, filename)
        
    def RunDongleTest(self, channel: int) -> bool:
        filename = "example" if self.filename.get() == "" else self.filename.get() 
        return self.backend.DongleTest(channel, dongle_freq, dongle_thresh, filename)

    def IncChannel(self):
        if(self.channel < max_channel):
            self.channel += 1
            self.text.set("Channel " + str(self.channel))
            self.backend.SetChannel(self.channel - 1)
            print(self.backend.arduino.ReadLine())

    def DecChannel(self):
        if(self.channel > 0):
            self.channel -= 1
            self.text.set("Channel " + str(self.channel))
            self.backend.SetChannel(self.channel - 1)
            print(self.backend.arduino.ReadLine())
            
    def GenerateReport(self):
        os.makedirs(os.path.dirname(self.filename.get() + 'report.csv'), exist_ok=True)
        file = open(self.filename.get() + 'report.csv', 'w')
        writer = csv.writer(file)
        
        writer.writerow(["Channel", "Impedance Test", "Dongle Test", "Pulse Echo Test"]);
        for (i, val) in enumerate(zip(self.passmap["Impedance"], self.passmap["Dongle"], self.passmap["PulseEcho"])):     
            writer.writerow(val.insert(0, i))
            
        file.close()

if __name__ == "__main__":

    gui = TesterFrontEnd()
    gui.Draw()

    
    
