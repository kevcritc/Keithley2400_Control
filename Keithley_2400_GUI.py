#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 18 18:23:27 2022

@author: phykc
"""
from tkinter import *
from threading import *
from math import sqrt
from time import sleep
import numpy as np
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from pymeasure.instruments.keithley import Keithley2400
from pymeasure.adapters import VISAAdapter
import pyvisa as visa

rm = visa.ResourceManager()
print('Device List is',rm.list_resources())

adapter=VISAAdapter("ASRL/dev/cu.usbserial-FTK20294::INSTR", timeout=None)
sourcemeter = Keithley2400(adapter)
class IVsweep():
    # Connect and configure the instrument might need to edit
    def collect_data(self):
        self.running=False
        self.sweep=True
        self.data_points = int(self.step_box.get())
        self.averages = int(self.ave_box.get())
        self.max_current = float(self.climit_box.get())
        if self.max_current>1:
            self.max_current=1.0
        self.startV=float(self.start_box.get())
        self.endV=float(self.end_box.get())
        self.prename=self.sample_box.get()
        self.val=self.CheckVar1.get()
        if self.startV>self.endV:
            self.startV, self.endV=self.endV, self.startV
        sourcemeter.reset()
        sourcemeter.use_front_terminals()
        sourcemeter.apply_voltage()
        sourcemeter.compliance_current=self.max_current
        sourcemeter.measure_current(current=self.max_current, auto_range=True)
        sleep(0.1) # wait here to give the instrument time to react
        sourcemeter.config_buffer(self.averages)
        sourcemeter.enable_source()
        sleep(0.1)
        if self.val==1:
            volt1=np.linspace(self.startV, self.endV, num=int(self.data_points/2))
            volt2=np.linspace(self.endV, self.startV, num=int(self.data_points/2))
            voltages=np.append(volt1, volt2)
        else:
        # Allocate arrays to store the measurement results
            voltages = np.linspace(self.startV, self.endV, num=int(self.data_points))
        currents = np.zeros_like(voltages)
        currentsstd = np.zeros_like(voltages)
       
        i=0
        # Loop through each current point, measure and record the voltage
        while i<len(voltages) and self.sweep:
            sourcemeter.source_voltage=voltages[i]
            sleep(0.1)
            currarray=np.array(sourcemeter.current)
            # Record the average and standard deviation
            currents[i] = np.mean(currarray)
            currentsstd[i] =np.std(currarray)
            i+=1
            
           
        sourcemeter.shutdown()    
        # Save the data columns in a CSV file
        data = pd.DataFrame({
            'Voltage (V)': voltages,
            'Current (A)': currents,
            'Current std (A)':currentsstd
        })
        # create a file name usine time date save it to the py code path.
        name=str(datetime.datetime.now())
        splitname=name.split('.')
        replace=splitname[0].replace(' ','_')
        filename=replace.replace(':','_')+'.csv'
        full_filename=self.sample_box.get()+filename
        data.to_csv(full_filename)
        # plot the data
        plt.xlabel('Voltage / V')
        plt.ylabel('Current, A')
        plt.errorbar(voltages,currents,yerr=currentsstd, color='black')
        plt.show()

# Set up threading for the manual control part


# Class for setting voltage manually and steping.
class Set_voltage:
    def apply(self):
        if not self.t2.is_alive():
            self.max_current = float(self.limit_box.get())
            if self.max_current>1.0:
                self.max_current=1.0
            self.setV=float(self.V_box.get())
            self.running=True
            sourcemeter.use_front_terminals()
            sourcemeter.apply_voltage()
            sourcemeter.measure_current(nplc=1,current=self.max_current, auto_range=0.1)
            sourcemeter.compliance_current=self.max_current
            sleep(0.1) # wait here to give the instrument time to react
            sourcemeter.sample_continuously()
            sourcemeter.source_voltage=self.setV
            sourcemeter.enable_source()
            sleep(0.1)
            while self.running:
                smc=sourcemeter.current
                sleep(0.2)
    def plus_volt(self):
        volts=float(self.V_box.get())
        step=float(self.V_step_box.get())
        self.V_box.delete(0, END)
        result=volts+step
        self.V_box.insert(0,"{:.3}".format(result))
        self.running=False
        sleep(1)
        self.threading1()
    def minus_volt(self):
        volts=float(self.V_box.get())
        step=float(self.V_step_box.get())
        self.V_box.delete(0, END)
        result=volts-step
        self.V_box.insert(0,"{:.3}".format(result))
        self.running=False
        sleep(1)
        self.threading1()
    def stop_voltage(self):
        self.sweep=False
        self.running=False
        sleep(1)
        sourcemeter.shutdown()
        
class App(IVsweep,Set_voltage):
    def __init__(self,master):
        self.master=master
        self.master.title('Keithley 2400 Control')
        row=0
        self.V_label=Label(self.master,text='V', anchor='w')
        self.V_label.grid(column=2,row=row,)
        self.start_label=Label(self.master,text='Start', anchor='e')
        self.start_label.grid(column=0,row=row,)
        self.start_box=Entry(self.master,width=4)
        self.start_box.grid(column=1,row=row)
        self.start_box.insert(0,'0.0')
        self.CheckVar1 = IntVar()
        self.check=Checkbutton(self.master,text='Complete Cycle',offvalue=0, onvalue=1, variable = self.CheckVar1)
        self.check.grid(column=3, row=row)
        row=1
        self.V_label=Label(self.master,text='V', anchor='w')
        self.V_label.grid(column=2,row=row,)
        self.end_label=Label(self.master,text='End',anchor='e')
        self.end_label.grid(column=0,row=row)
        self.end_box=Entry(self.master,width=4)
        self.end_box.insert(0,'10.0')
        self.end_box.grid(column=1,row=row)
        row=2
        self.step_label=Label(self.master,text='Number of Data points',anchor='e')
        self.step_label.grid(column=0,row=row)
        self.step_box=Entry(self.master,width=4)
        self.step_box.grid(column=1,row=row)
        self.step_box.insert(0,'20')
        row=3
        self.ave_label=Label(self.master,text='Averages',anchor='e')
        self.ave_label.grid(column=0,row=row)
        self.ave_box=Entry(self.master,width=4)
        self.ave_box.insert(0,'10')
        self.ave_box.grid(column=1,row=3)
        row=4
        self.I_label=Label(self.master,text='A',anchor='w')
        self.I_label.grid(column=2,row=row,)
        self.climit_label=Label(self.master,text='Current Limit',anchor='e')
        self.climit_label.grid(column=0,row=row)
        self.climit_box=Entry(self.master,width=4)
        self.climit_box.grid(column=1,row=row)
        self.climit_box.insert(0,'10E-3')
        
        row=8
        self.set_limit_label1=Label(self.master,text='Current Limit')
        self.set_limit_label1.grid(column=0, row=row)
        self.limit_box=Entry(self.master,width=4)
        self.limit_box.grid(column=1,row=row)
        self.limit_box.insert(0,'10E-3')
        
        
        row=9
        self.set_volts_label1=Label(self.master,text='Voltage')
        self.set_volts_label1.grid(column=0, row=row)
        self.V_box=Entry(self.master,width=4)
        self.V_box.grid(column=1,row=row)
        self.V_box.insert(0,'1.00')
        self.V_label=Label(self.master,text='Step +/-', anchor='w')
        self.V_label.grid(column=2,row=row,)
        self.V_step_box=Entry(self.master,width=4)
        self.V_step_box.grid(column=3,row=row)
        self.V_step_box.insert(0,'0.1')
        
        
        row=5
        self.sample_label=Label(self.master,text='Sample Name',anchor='e')
        self.sample_label.grid(column=2,row=row)
        self.sample_box=Entry(self.master,width=10)
        self.sample_box.grid(column=3,row=row)

        self.button=Button(self.master,text='Run', command=self.threading2)
        self.button.grid(column=3,row=6)
        self.set_volts_label=Label(self.master,text='Manual Control')
        self.set_volts_label.grid(column=0, row=7)
        
        row=10
        self.go_button=Button(self.master,text='Go', command=self.threading1)
        self.go_button.grid(column=0, row=row)
        self.plus_button=Button(self.master,text='+', command=self.plus_volt)
        self.plus_button.grid(column=1, row=row)
        self.minus_button=Button(self.master,text='-', command=self.minus_volt)
        self.minus_button.grid(column=2, row=row)
        
        row=11
        self.stop_button=Button(self.master,text='Stop', command=self.stop_voltage)
        self.stop_button.grid(column=0, row=row)
        super().__init__()
        
    def threading1(self):
        t1=Thread(target=self.apply)
        t1.start()
    def threading2(self):
        self.t2=Thread(target=self.collect_data)
        self.t2.start()



root=Tk()

app=App(root)

mainloop()

sourcemeter.shutdown()
