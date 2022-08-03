
from tkinter import StringVar, ttk, Tk, IntVar, Toplevel
import time
import TesterBackend as tb
import csv
import os
import threading
import openpyxl
from openpyxl.styles import fills, colors
from copy import copy

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
        self.passmap = { "Impedance": [[False, None]] * tb.max_channel, "PulseEcho": [[False, None, None, None]] * tb.max_channel, "Dongle": [[False, None]] * tb.max_channel}
        self.backend = tb.CatheterTester() # Backend tester that does the actual work 
        self.triggered = IntVar(self.root, 0)

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
        self.reportbutton = ttk.Button(self.root, text = "Generate Report", command = self.GenerateXLSXReport)

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
        self.filenamelabel.place(x = 50, y = 200)
        self.filename.place(x = 300, y = 200, height = 50, width = 250)

        self.window.mainloop()
            
    def RunSingleChannelTest(self, channel, filename) -> None:

        if(self.impedancetest.get() != 0 or self.dongletest.get() != 0 or self.pulseechotest.get() != 0): # repeat the same process with the impedance test/dongle test
            channel &= ~vnachanneloffset
        else:
            channel |= vnachanneloffset

        self.backend.SetChannel(channel - 1)

        print(f"Running Test on Channel: {channel}")
    
        if self.pulseechotest.get() != 0:
            self.passmap["PulseEcho"][channel - 1] = self.RunPulseEchoTest(channel, filename) # Run the Tests and record the Results

        if self.impedancetest.get() != 0:
            self.passmap["Impedance"][channel - 1] = self.RunImpedanceTest(channel, filename) 

        if self.dongletest.get() != 0:
            self.passmap["Dongle"][channel - 1] =  self.RunDongleTest(channel, filename) 
    
    def RunTests(self) -> None:
        
        if(self.impedancetest.get() == 0 and self.dongletest.get() == 0 and self.pulseechotest.get() == 0): # repeat the same process with the impedance test/dongle test
            return
    
        filename = os.getcwd() + '\\' + self.filename.get() 
        path = "\\".join(filename.split("\\")[0:-1]) # create the path of the file if it wasn't already there

        os.makedirs(path, exist_ok=True)
        
        if self.allchannels.get() != 0:
            for i in range(tb.max_channel):
                self.RunSingleChannelTest(i + 1, filename)
            
            self.GenerateXLSXReport()

        else:
            self.RunSingleChannelTest(self.channel, filename)
            
    def CapturePopup(self) -> None:
        
        window = Toplevel()
        
        def CaptureButtonCB() -> None:
            self.triggered.set(1)
            window.destroy()
                
        button = ttk.Button(window, text = "Capture", command = CaptureButtonCB)
        button.pack()
        button.wait_variable(self.triggered)

    def RunImpedanceTest(self, channel, filename) -> tuple[bool, float, float, float]:
        print("Running Impedance Test")
        return self.backend.ImpedanceTest(channel, filename) # run the test with the filename

    def RunPulseEchoTest(self, channel, filename) -> tuple[bool, float]:    
        self.CapturePopup()
        self.triggered.set(0)
        print("Running Pulse Echo Test")
        return self.backend.PulseEchoTest(1, channel, filename) # run the test on scope channel 1 with file name filename
        
    def RunDongleTest(self, channel, filename) -> tuple[bool, float]:
        print("Running Dongle Test")
        return self.backend.DongleTest(channel, filename) # Run the Dongle test with the Filename as its file name

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
            
    def GenerateCSVReport(self) -> None: # Generates a CSV Report with all of the results

        filename = os.getcwd() + '\\' + self.filename.get() 
        channels = [i + 1 for i in range(tb.max_channel)]

        with open(filename + 'PEReport.csv', 'w') as pefile:
            pewriter = csv.writer(pefile)
            
            pewriter.writerow(["Channel", "Passed", "Vpp", "Bandwidth", "Center Frequency"])
            for channel in channels:
                print(self.passmap["PulseEcho"][channel - 1])
                data = self.passmap["PulseEcho"][channel - 1]
                data.insert(0, channel)
                pewriter.writerow(data)

        with open(filename + 'ZReport.csv', 'w') as zfile:
            zwriter = csv.writer(zfile)
            
            zwriter.writerow(["Channel", "Passed", "Capacitance"])
            for channel in channels:
                print(self.passmap["Impedance"][channel - 1])
                data = self.passmap["Impedance"][channel - 1]
                data.insert(0, channel)
                zwriter.writerow(data)
        
        with open(filename + "DongleReport", 'w') as donglefile:
            donglewriter = csv.writer(donglefile)
            
            donglewriter.writerow(["Channel", "Passed", "Capacitance"])
            for channel in channels:
                print(self.passmap["Dongle"][channel - 1])
                data = self.passmap["Dongle"][channel - 1]
                data.insert(0, channel)
                donglewriter.writerow(data)

    def GenerateXLSXReport(self) -> None:

        report = openpyxl.Workbook()
        
        templatepath = os.path.dirname(os.path.abspath(__file__)) + "\\..\\docs\\"
        donglereporttemplate = openpyxl.load_workbook(filename = templatepath + "DongleTemplate.xlsx")
        impedancereporttemplate = openpyxl.load_workbook(filename = templatepath + "ImpedanceTemplate.xlsx")
        pereporttemplate = openpyxl.load_workbook(filename = templatepath + "PETemplate.xlsx")
        
        donglereport = report.active
        donglereport.title = "Dongle"
        copy_sheet(donglereporttemplate.active, donglereport)
        impedancereport = report.create_sheet("Impedance")
        copy_sheet(impedancereporttemplate.active, impedancereport)
        pereport = report.create_sheet("Pulse Echo")
        copy_sheet(pereporttemplate.active, pereport)
        
        red = colors.Color("00FF0000")
        green = colors.Color("0000FF00")
        failcolor = fills.PatternFill(patternType = 'solid', fgColor = red)
        passcolor = fills.PatternFill(patternType = 'solid', fgColor = green)
        
        for i in range(8, 8 + tb.max_channel):
            
            data = self.passmap["PulseEcho"][i - 8]
            if None in data:
                continue
            
            pereport["D" + str(i)] = f"{data[1] * 1e3: .2f}"
            pereport["E" + str(i)] = f"{data[3] * 1e-6: .2f}"
            pereport["F" + str(i)] = "Pass" if data[0] else "Fail"
            pereport["G" + str(i)] = "True" if data[1] == 0 else ""
            pereport["H" + str(i)] = f"{data[2] * 10e-6:.2f}"
            
            color = passcolor if data[0] == True else failcolor
            rowcells = pereport.iter_cols(min_col = 3, max_col = 8, min_row = i, max_row = i)
            for row in rowcells:
                for cols in row: 
                    cols.fill = color
            
        for i in range(11, 11 + tb.max_channel):    

            data = self.passmap["Impedance"][i - 11]
            if None in data:
                continue
            
            impedancereport["D" + str(i)] = f"{data[1] * 1e12: .2f}"
            impedancereport["E" + str(i)] = "Pass" if data[0] else "Fail"     
            impedancereport["F" + str(i)] = "Open" if data[1] > 10e-12 and data[i] < 600e-12 else "Short" if data[1] < 0 else ""       
            
            color = passcolor if data[0] == True else failcolor
            rowcells = impedancereport.iter_cols(min_col = 3, max_col = 6, min_row = i, max_row = i)
            for row in rowcells:
                for cols in row: 
                    cols.fill = color

        for i in range(11, 11 + tb.max_channel):    
            
            data = self.passmap["Dongle"][i - 11]
            if None in data:
                continue
                
            donglereport["D" + str(i)] = f"{data[1] * 1e12: .2f}"
            donglereport["E" + str(i)] = "Pass" if data[0] else "Fail"
            donglereport["F" + str(i)] = "Open" if data[1] > 10e-12 and data[1] < 180e-12 else "Short" if data[1] < 0 else ""
            
            color = passcolor if data[0] == True else failcolor
            rowcells = donglereport.iter_cols(min_col = 3, max_col = 6, min_row = i, max_row = i)
            for row in rowcells:
                for cols in row: 
                    cols.fill = color
                
        filename = os.getcwd() + '\\' + self.filename.get() + "Report.xlsx"
        report.save(filename)


def copy_sheet(source_sheet, target_sheet):
    copy_cells(source_sheet, target_sheet)  # copy all the cel values and styles
    copy_sheet_attributes(source_sheet, target_sheet)

def copy_sheet_attributes(source_sheet, target_sheet):
    target_sheet.sheet_format = copy(source_sheet.sheet_format)
    target_sheet.sheet_properties = copy(source_sheet.sheet_properties)
    target_sheet.merged_cells = copy(source_sheet.merged_cells)
    target_sheet.page_margins = copy(source_sheet.page_margins)
    target_sheet.freeze_panes = copy(source_sheet.freeze_panes)

    # set row dimensions
    # So you cannot copy the row_dimensions attribute. Does not work (because of meta data in the attribute I think). So we copy every row's row_dimensions. That seems to work.
    for rn in range(len(source_sheet.row_dimensions)):
        target_sheet.row_dimensions[rn] = copy(source_sheet.row_dimensions[rn])

    if source_sheet.sheet_format.defaultColWidth is None:
        print('Unable to copy default column wide')
    else:
        target_sheet.sheet_format.defaultColWidth = copy(source_sheet.sheet_format.defaultColWidth)

    # set specific column width and hidden property
    # we cannot copy the entire column_dimensions attribute so we copy selected attributes
    for key, value in source_sheet.column_dimensions.items():
        target_sheet.column_dimensions[key].min = copy(source_sheet.column_dimensions[key].min)   # Excel actually groups multiple columns under 1 key. Use the min max attribute to also group the columns in the targetSheet
        target_sheet.column_dimensions[key].max = copy(source_sheet.column_dimensions[key].max)  # https://stackoverflow.com/questions/36417278/openpyxl-can-not-read-consecutive-hidden-columns discussed the issue. Note that this is also the case for the width, not onl;y the hidden property
        target_sheet.column_dimensions[key].width = copy(source_sheet.column_dimensions[key].width) # set width for every column
        target_sheet.column_dimensions[key].hidden = copy(source_sheet.column_dimensions[key].hidden)

def copy_cells(source_sheet, target_sheet):
    for (row, col), source_cell in source_sheet._cells.items():
        target_cell = target_sheet.cell(column=col, row=row)

        target_cell._value = source_cell._value
        target_cell.data_type = source_cell.data_type

        if source_cell.has_style:
            target_cell.font = copy(source_cell.font)
            target_cell.border = copy(source_cell.border)
            target_cell.fill = copy(source_cell.fill)
            target_cell.number_format = copy(source_cell.number_format)
            target_cell.protection = copy(source_cell.protection)
            target_cell.alignment = copy(source_cell.alignment)

        if source_cell.hyperlink:
            target_cell._hyperlink = copy(source_cell.hyperlink)

        if source_cell.comment:
            target_cell.comment = copy(source_cell.comment)
            

if __name__ == "__main__":

    import atexit
    atexit.register(input, "Press Any Key To Continue")

    gui = TesterFrontEnd()
    gui.Draw()

    
    
