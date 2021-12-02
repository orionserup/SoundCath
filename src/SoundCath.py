
import pyvisa as visa
import csv
from tkinter import StringVar, ttk, Tk, IntVar
import serial
from serial.tools.list_ports import comports
import time

max_channel = 64  # max number of addressable channels on the chip
scope_interval_us = 3 # how long of a waveform to capture
scope_sample_interval_ns = 1 # sampling period of oscilloscope
channel_switch_interval = .5 # when running all channels the time between channels
oscilloscope_channel = 3 # oscilloscope channel

class CatheterTester:

    def __init__(self):
        
        self.Arduino = self.ConnectToArduino()
        self.Oscilloscope = self.ConnectToScope()

        # if self.Arduino == None:  # if could not connect to the arduino
        #     print("Could Not Connect To the Arduino, Exiting")
        #     input("Press Any Key To Exit")
        #     exit() # leave the program
                
    def ImpedanceTest(self, channel: int, duration: float, filename: str) -> None:
        pass

    def PulseEchoTest(self, channel: int, duration: float, filename: str) -> None:
        pass

    def ConnectToArduino(self) -> serial.Serial:

        all_ports = comports()
        print("Listing Serial Ports: ")
        ports = set()
        
        for port, _, _ in all_ports: # for every detected port add it to a set of port names
            ports |= {port}
            print(str(port))

        for port in ports:  # for every port in the set try to connect to it

            try:
                dev = serial.Serial(str(port), timeout = .2)
            except serial.SerialException: # if there is an issue with the port go onto the next one
                continue

            dev.write((10).to_bytes(1, 'big')) # send an echo test
            if dev.read(1) == (10).to_bytes(1, 'big'): # if the echo tests passes return that port
                print("Connected To Arduino on Port:  " + str(port))
                return dev

        print("Could Not Connect To A Valid Arduino Serial Port")
        return None

    def ConnectToScope(self) -> visa.Resource:
        
        rm = visa.ResourceManager() # create a VISA device manager
        devlist = rm.list_resources()  # print out all of the possible VISA Devices
        print("Listing VISA Devices: {}".format(devlist))
        
        for dev in devlist:
            try:
                scope = rm.open_resource(dev) # open the device for use
                scope.query("*IDN?")
                
            except visa.VisaIOError:
                scope = None
                continue
            
            if scope != None:
                print("Connected To a Scope: {}".format(dev))
                print("Scope ID: " + scope.query("*IDN?"))
                return scope

        print("Did Not Find A Valid Scope")
        return None

    def SetChannel(self, channel: int):

        self.Arduino.write(channel.to_bytes(1, 'big'))

    def GetScopeData(self, channel: int, filename: str):

        self.scope.write("HEADER OFF")
        self.scope.write("DATa:SOURCe ch{}".format(channel))
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
        yunit = self.scope.query('WFMOUTPRE:YUNIT?')
        ymult = self.scope.query('WFMOUTPRE:YMULT?')
        yoff = self.scope.query('WFMOUTPRE:YOFF?')
        yzero = self.scope.query('WFMOUTPRE:YZERO?')

        inc_us = float(inc) * 1000000
        stop = int(float(scope_interval_us)/float(inc_us))

        self.scope.write("DATA:STOP {}".format(num_samples if stop > num_samples else stop))

        values = self.scope.query_binary_values("CURVE?", datatype = "b", )

        time = [i * float(inc) for i in range(stop)]
        voltage = [float(ymult)*(values[i] - float(yoff)) - float(yzero) for i in range(stop)]
        
        writer = csv.writer(open(filename, "w"))
     
        writer.writerow(["Time", "Voltage"])
        for i in range(stop):
            writer.writerow([time[i], voltage[i]])

class TesterFrontEnd:  # a GUI front end for the test
   
    def __init__(self):

        self.root = Tk() # setup the GUI base
        self.root.title("Catheter Tester Script")
        self.root.geometry("600x400")
        self.style = ttk.Style()
        self.style.configure("Orion.TCheckbutton", font = ("Arial", 16))
        self.style.configure("Orion.TButton", font = ("Arial", 18))
        self.style.configure("Orion.TEntry", font = ("Arial", 24))
        self.style.configure("Orion.TLabel", font = ("Arial", 18))

        self.channel = 0
        self.impedancetest = IntVar(self.root, 0) # all private variables
        self.allchannels = IntVar(self.root, 0)
        self.pulseechotest = IntVar(self.root, 0)
        self.text = StringVar(self.root, "Channel " + str(self.channel))
        self.backend = CatheterTester()

        self.window = ttk.Frame(self.root)  # All widget elemets
        self.upbutton = ttk.Button(self.root, text = "Up", command = self.IncChannel, style = "Orion.TButton")
        self.downbutton = ttk.Button(self.root, text = "Down", command = self.DecChannel, style = "Orion.TButton")
        self.label = ttk.Label(self.root, textvariable = self.text, width = 11, style = "Orion.TLabel")
        self.filenamelabel = ttk.Label(self.root, text = "File Name to Save:", style = "Orion.TLabel" )

        self.impedancetestbutton = ttk.Checkbutton(self.root, variable = self.impedancetest, text = "Impedance Test", style = "Orion.TCheckbutton")
        self.allchannelsbutton  = ttk.Checkbutton(self.root, variable = self.allchannels,  text = "Run All Channels" , style = "Orion.TCheckbutton")
        self.pulseechotestbutton = ttk.Checkbutton(self.root, variable = self.pulseechotest, text = "Pulse Echo", style = "Orion.TCheckbutton")
        
        self.runbutton = ttk.Button(self.root, text = "Run Tests", command = self.RunTests, style = "Orion.TButton")
        self.filename = ttk.Entry(self.root, text = "File Name", style = "Orion.TEntry" )

    def Draw(self): # positions and draws all of the widgets in the frame

        self.upbutton.place(x = 400, y = 50)
        self.label.place(x = 240 , y = 50)
        self.downbutton.place(x = 50, y = 50)

        self.impedancetestbutton.place(x = 50, y = 100)
        self.pulseechotestbutton.place(x = 250, y = 100)
        self.allchannelsbutton.place(x = 400, y = 100)

        self.runbutton.place(x = 400, y = 300)
        self.filenamelabel.place(x = 50, y = 200)
        self.filename.place(x = 300, y = 200, height = 50, width = 250)

        self.window.mainloop()

    def RunTests(self): # run the tests according to the parameters

        if self.allchannels.get():

            for i in range(max_channel):
                
                self.backend.SetChannel(i)

                if self.pulseecho.get():
                    self.RunPulseEchoTest()
            
                if self.impedance.get():
                    self.RunImpedanceTest()

                time.sleep(channel_switch_interval)

        else: 

            if self.pulseecho.get():
                self.RunPulseEchoTest()
            
            if self.impedance.get():
                self.RunImpedanceTest()
            
    def RunImpedanceTest(self):

        self.backend.ImpedanceTest()

    def RunPulseEchoTest(self):

        pass

    def IncChannel(self):

        if(self.channel < max_channel):
            self.channel += 1
            self.text.set("Channel " + str(self.channel))
            self.backend.SetChannel(self.channel)

    def DecChannel(self):
        
        if(self.channel > 0):
            self.channel -= 1
            self.text.set("Channel " + str(self.channel))
            self.backend.SetChannel(self.channel)

    
if __name__ == "__main__":

    gui = TesterFrontEnd()
    gui.Draw()
