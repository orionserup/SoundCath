from tkinter import StringVar, ttk, Tk, IntVar
import time
import TesterBackend as tb

channel_switch_interval = .5 # when running all channels the time between channels
max_channel = 64
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
        self.text = StringVar(self.root, "Channel " + str(self.channel))

        self.haspassed = False

        #self.backend = tb.CatheterTester()

        self.window = ttk.Frame(self.root)  # All widget elements
        self.upbutton = ttk.Button(self.root, text = "Up", command = self.IncChannel)
        self.downbutton = ttk.Button(self.root, text = "Down", command = self.DecChannel)
        self.label = ttk.Label(self.root, textvariable = self.text, width = 11)
        self.filenamelabel = ttk.Label(self.root, text = "File Name to Save:")

        self.impedancetestbutton = ttk.Checkbutton(self.root, variable = self.impedancetest, text = "Impedance Test")
        self.allchannelsbutton  = ttk.Checkbutton(self.root, variable = self.allchannels,  text = "Run All Channels")
        self.pulseechotestbutton = ttk.Checkbutton(self.root, variable = self.pulseechotest, text = "Pulse Echo")

        self.runbutton = ttk.Button(self.root, text = "Run Tests", command = self.RunTests)
        self.filename = ttk.Entry(self.root, text = "File Name")

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

    def DisplayPassWindow(self) -> None:
        PassWindow = Tk()
        PassWindow.geometry('100x200')

        def Pass():
            self.haspassed = True
            PassWindow.destroy()

        def Fail():
            self.haspassed = False
            PassWindow.destroy()

        passbutton = ttk.Button(PassWindow, text = "Pass", command = Pass)
        failbutton = ttk.Button(PassWindow, text = "Fail", command = Fail)
        passbutton.place(x = 0, y = 0, height = 100, width = 100)
        failbutton.place(x = 0, y = 100, height = 100, width = 100)

        PassWindow.mainloop()

    def RunTests(self): # run the tests according to the parameters
        print(self.haspassed)
        if self.allchannels.get() != 0:
            for i in range(max_channel):
                
                self.backend.SetChannel(i)
                if self.pulseechotest.get():
                    self.RunPulseEchoTest()
                if self.impedancetest.get():
                    self.RunImpedanceTest()
                self.DisplayPassWindow()
                time.sleep(channel_switch_interval)
        else: 
            if self.pulseechotest.get() != 0:
                self.RunPulseEchoTest()
            if self.impedancetest.get() != 0:
                self.RunImpedanceTest()

            self.DisplayPassWindow()

    def RunImpedanceTest(self):
        self.backend.ImpedanceTest()

    def RunPulseEchoTest(self):    
        self.backend.PulseEchoTest()

    def IncChannel(self):
        if(self.channel < max_channel):
            self.channel += 1
            self.text.set("Channel " + str(self.channel))
            tb.SetChannel(self.channel)

    def DecChannel(self):
        if(self.channel > 0):
            self.channel -= 1
            self.text.set("Channel " + str(self.channel))
            tb.SetChannel(self.channel)

if __name__ == "__main__":

    gui = TesterFrontEnd()
    gui.Draw()
