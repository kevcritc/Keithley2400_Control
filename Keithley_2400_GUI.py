#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 18 18:23:27 2022

@author: phykc
"""
from tkinter import *
from queue import Queue
from threading import *
import time
import numpy as np
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  NavigationToolbar2Tk)
from pymeasure.instruments.keithley import Keithley2400
from pymeasure.adapters import VISAAdapter
import pyvisa as visa
from tkinter import messagebox,filedialog
import os
import warnings

class IVsweep():
    # Connect and configure the instrument might need to edit
    # Either uses loop values or V1 to V2  method.
    def collect_data(self):
        self.dialoge_queue.put('Setting up measurement')
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
        self.sourcemeter.reset()
        self.sourcemeter.use_front_terminals()
        self.sourcemeter.apply_voltage()
        self.sourcemeter.compliance_current=self.max_current
        self.sourcemeter.measure_current(current=self.max_current, auto_range=True)
        time.sleep(0.1) # wait here to give the instrument time to react
        self.sourcemeter.config_buffer(self.averages)
        self.sourcemeter.enable_source()
        time.sleep(0.1)
        if self.val==1:
            startnode=float(self.startnode.get())
            highnode=float(self.highnode.get())
            lownode=float(self.lownode.get())
            step_val=float(self.stepsize.get())
            volt1=np.arange(startnode,highnode,step_val)
            volt2=np.arange(highnode,lownode,-1*step_val)
            volt3=np.arange(lownode,startnode+step_val,step_val)
            numberofloops=int(self.loopno.get())
            self.voltages=np.concatenate((volt1, volt2, volt3))
            voltagescopy=self.voltages.copy()
            for n in range(numberofloops-1):      
                self.voltages=np.concatenate((self.voltages,voltagescopy))
        else:
        # Allocate arrays to store the measurement results
            self.voltages = np.linspace(self.startV, self.endV, num=int(self.data_points))
        self.run_volts()
    def run_volts(self):
        self.dialoge_queue.put('Measuring')
       
        currents = np.zeros_like(self.voltages)
        currentsstd = np.zeros_like(self.voltages)
        i=0
        # Loop through each current point, measure and record the voltage
        while i<len(self.voltages) and self.sweep and self.running:
            self.sourcemeter.source_voltage=self.voltages[i]
            time.sleep(0.1)
            currarray=np.array(self.sourcemeter.current)
            # Record the average and standard deviation
            currents[i] = np.mean(currarray)
            currentsstd[i] =np.std(currarray)
            i+=1
        self.dialoge_queue.put('Saving data')
        self.sourcemeter.shutdown()    
        # Save the data columns in a CSV file
        data = pd.DataFrame({
            'Voltage (V)': self.voltages,
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
        self.dialoge_queue.put(f'Data saved to {full_filename}')
        

class IVsweep4probe():
    # Connect and configure the instrument might need to edit
    # Either uses loop values or V1 to V2  method.
    def collect_data1(self, queue):
        self.dialoge_queue.put('Setting up measurement')
        self.running=True
        self.sweep=True
        self.queue=queue
        self.data_points = int(self.step_box.get())
        self.averages = int(self.ave_box.get())
        self.max_volt = float(self.vlimit_box.get())
        if abs(self.max_volt)>199:
            self.max_volt=199
        self.dialoge_queue.put(f'Max voltage allowed is {self.max_volt}')
        self.startI=float(self.start_box.get())
        self.endI=float(self.end_box.get())
        self.prename=self.sample_box.get()
        self.val=self.CheckVar1.get()
        if self.startI>self.endI:
            self.startI, self.endI=self.endI, self.startI
        self.sourcemeter.reset()
        self.sourcemeter.use_front_terminals()
        self.sourcemeter.apply_current()
        self.sourcemeter.compliance_voltage=self.max_volt
        self.sourcemeter.measure_voltage(voltage=self.max_volt, auto_range=True)
        time.sleep(0.1) # wait here to give the instrument time to react
        self.sourcemeter.config_buffer(self.averages)
        self.sourcemeter.enable_source()
        time.sleep(0.1)
        self.dialoge_queue.put('Sourcemeter is ready')
        if self.val==1:
            startnode=float(self.startnode.get())
            highnode=float(self.highnode.get())
            lownode=float(self.lownode.get())
            step_val=float(self.stepsize.get())
            amp1=np.arange(startnode,highnode,step_val)
            amp2=np.arange(highnode,lownode,-1*step_val)
            amp3=np.arange(lownode,startnode+step_val,step_val)
            numberofloops=int(self.loopno.get())
            self.amps=np.concatenate((amp1, amp2, amp3))
            ampscopy=self.amps.copy()
            for n in range(numberofloops-1):      
                self.amps=np.concatenate((self.amps,ampscopy))
        else:
        # Allocate arrays to store the measurement results
            self.amps = np.linspace(self.startI, self.endI, num=int(self.data_points))
        self.run_amps()
        
    def run_amps(self):
        
        volts = np.zeros_like(self.amps)
        voltsstd = np.zeros_like(self.amps)
        i=0
        self.dialoge_queue.put('Running measurement')
        # Loop through each voltage point, measure and record the voltage
        while i<len(self.amps) and self.sweep and self.running:
            self.sourcemeter.source_current=self.amps[i]
            time.sleep(0.1)
            voltsarray=np.array(self.sourcemeter.voltage)
            # Record the average and standard deviation
            volts[i] = np.mean(voltsarray)
            voltsstd[i] =np.std(voltsarray)
            self.data_queue.put([self.amps[:i], volts[:i], voltsstd[:i]])   
            i+=1
        self.sourcemeter.shutdown()   
        self.dialoge_queue.put('Stopping measurement')
        # Save the data columns in a CSV file
        data = pd.DataFrame({
            
            'Current (A)': self.amps,
            'Voltage mean (V)': volts,
            'Voltage std (A)':voltsstd,
            'Current (µA)': self.amps * 1000000,
            'Voltage mean (mV)': volts * 1000,
            'Voltage std (mV)': voltsstd*1000
        })
        # create a file name usine time date save it to the py code path.
        name=str(datetime.datetime.now())
        splitname=name.split('.')
        replace=splitname[0].replace(' ','_')
        filename=replace.replace(':','_')+'.csv'
        
        full_filename = os.path.join(self.save_dir.get(), self.sample_box.get() + filename)
        df=pd.DataFrame(data)
        df.to_csv(full_filename)
        self.dialoge_queue.put(f'Data saved to{full_filename}')
        self.running=False
        
        

# Set up threading for the manual control part


# Class for setting voltage manually and steping.
class Set_voltage:
    def man_V(self):
        self.dialoge_queue.put('Manual Voltage Initalising')
        self.max_current = float(self.Vlimit_box.get())
        if self.max_current>1.0:
            self.max_current=1.0
        self.setV=float(self.V_box.get())
        self.running=True
        self.sourcemeter.use_front_terminals()
        self.sourcemeter.apply_voltage()
        self.sourcemeter.measure_current(nplc=1,current=self.max_current, auto_range=0.1)
        self.sourcemeter.compliance_current=self.max_current
        time.sleep(0.1) # wait here to give the instrument time to react
        self.sourcemeter.sample_continuously()
        self.sourcemeter.source_voltage=self.setV
        self.sourcemeter.enable_source()
        time.sleep(0.1)
        while self.running:
            smc=self.sourcemeter.current
            time.sleep(0.2)
        
    def apply(self):
        try:
            if not self.t2.is_alive():
                self.man_V()
                
        except AttributeError:
            self.man_V()
            
    def plus_volt(self):
        volts=float(self.V_box.get())
        step=float(self.V_step_box.get())
        self.V_box.delete(0, END)
        result=volts+step
        self.V_box.insert(0,"{:.3}".format(result))
        self.running=False
        time.sleep(1)
        self.threading1()
    def minus_volt(self):
        volts=float(self.V_box.get())
        step=float(self.V_step_box.get())
        self.V_box.delete(0, END)
        result=volts-step
        self.V_box.insert(0,"{:.3}".format(result))
        self.running=False
        time.sleep(1)
        self.threading1()
    def stop_voltage(self):
        self.sweep = False
        self.running = False
        time.sleep(1)
        self.safe_shutdown()

# Class for logging current for a voltage manually and steping.        
class Log_current:
    def log_I(self, time_data_queue):
        self.dialoge_queue.put('Initalising a time log')
        self.time_data_queue=time_data_queue
        self.currentlog=[]
        self.currentlogstd=[]
        self.timelog=[]
        self.max_current = float(self.currentmax_set.get())
        if self.max_current>1.0:
            self.max_current=1.0
        self.setV=float(self.volts_set.get())
        self.running=True
        time.sleep(0.1) 
        self.sourcemeter.use_front_terminals()
        time.sleep(0.1) 
        self.sourcemeter.apply_voltage()
        time.sleep(0.1) 
        self.sourcemeter.source_mode = 'voltage'
        time.sleep(0.1) 
        self.sourcemeter.measure_current(nplc=0.01,current=self.max_current, auto_range=0.1)
        time.sleep(0.1) 
        self.sourcemeter.compliance_current=self.max_current
        time.sleep(0.1) # wait here to give the instrument time to react
        self.dialoge_queue.put('Starting..')
        self.maxtime=int(self.time_stop_set.get())
        
        self.sourcemeter.sample_continuously()
        
        self.sourcemeter.source_voltage=self.setV
        self.sourcemeter.enable_source()
        
        time.sleep(0.1)
        start_time = time.time()
        interval=float(self.time_inter_set.get())
        
        # fudge to get it 
        inter_mod=interval-0.7275
        if inter_mod<0:
            inter_mod=0.0
            self.dialoge_queue.put('The sampling takes about 0.7s - it is possible to reduce but will require some changes')
            
        
        while self.running:
            
            self.currentlog.append(np.mean(self.sourcemeter.current))
            self.currentlogstd.append(np.std(self.sourcemeter.current)/np.sqrt(len(self.sourcemeter.current)))
            current_time = time.time()
            self.timelog.append(current_time-start_time)
            time.sleep(inter_mod)
            if current_time-start_time>self.maxtime:
                self.stop_voltage()
            data=[self.timelog,self.currentlog,self.currentlogstd]
            self.time_data_queue.put(data)
        self.dialoge_queue.put('Stopped')
        self.save_data()
        
    def save_data(self):
        self.dialoge_queue.put('Saving data')
        data = pd.DataFrame({
            
            'Time (s)': self.timelog,
            'Current (A)': self.currentlog,
            'Current error (A)': self.currentlogstd
            
        })
        # create a file name usine time date save it to the py code path.
        name=str(datetime.datetime.now())
        splitname=name.split('.')
        replace=splitname[0].replace(' ','_')
        filename=replace.replace(':','_')+'.csv'
        save_path = self.time_log_dir.get()
        if not save_path:
            self.dialoge_queue.put("No time log directory selected — using default path.")
            save_path = os.getcwd()
        
        full_filename = os.path.join(save_path, self.f_name.get() + filename)
        df=pd.DataFrame(data)
        df.to_csv(full_filename)
        self.dialoge_queue.put(f'Saved {full_filename}')
        
        
        
        
            
            
    

class App(IVsweep4probe,Set_voltage, Log_current):
    def __init__(self,master, sourcemeter):
        self.sourcemeter=sourcemeter
        self.statecol=NORMAL
        self.master=master
        self.master.title('Keithley 2400 4-Probe Control')
        
        self.data_queue=Queue()
        self.time_data_queue=Queue()
        self.dialoge_queue = Queue()
        
        self.running=False
        
        # Inside frame1 is the IV selection
        self.frame1=LabelFrame(self.master, text='I-V Sweep Settings', padx=10, pady=56)
        self.frame1.grid(column=1, row=1, padx=10)
        self.I_label=Label(self.frame1,text='A', anchor='w')
        self.I_label.grid(column=2,row=0)
        self.start_label=Label(self.frame1,text='Start', anchor='e')
        self.start_label.grid(column=0,row=0,sticky='e')
        self.start_box=Entry(self.frame1,width=12,justify='right')
        self.start_box.grid(column=1,row=0)
        self.start_box.insert(0,'0.0')
        self.I_label=Label(self.frame1,text='A', anchor='w')
        self.I_label.grid(column=2,row=1)
        self.end_label=Label(self.frame1,text='End',anchor='e')
        self.end_label.grid(column=0,row=1,sticky='e')
        self.end_box=Entry(self.frame1,width=12,justify='right')
        self.end_box.insert(0,'1E-6')
        self.end_box.grid(column=1,row=1)
        self.step_label=Label(self.frame1,text='No. Data points',anchor='e')
        self.step_label.grid(column=0,row=2,sticky='e')
        self.step_box=Entry(self.frame1,width=12,justify='right')
        self.step_box.grid(column=1,row=2)
        self.step_box.insert(0,'20')
        
        # Loop control
        self.frame4=LabelFrame(self.master, text='Full Loop Control', padx=10, pady=42)
        self.frame4.grid(column=2,row=1, padx=10)
        
        self.n1_label=Label(self.frame4,text='I min')
        self.n2_label=Label(self.frame4,text='I start')
        self.n3_label=Label(self.frame4,text='I max')
        self.n4_label=Label(self.frame4,text='I step')
        self.n1_label.grid(column=0, row=2, sticky='e')
        self.n2_label.grid(column=0, row=0,sticky='e')
        self.n3_label.grid(column=0, row=1,sticky='e')
        self.n4_label.grid(column=0, row=3, sticky='e')
        self.lownode=Entry(self.frame4, width=12, justify='right')
        self.highnode=Entry(self.frame4, width=12, justify='right')
        self.startnode=Entry(self.frame4, width=12, justify='right')
        self.stepsize=Entry(self.frame4, width=12, justify='right')
        self.lownode.insert(0,'-20E-7')
        self.highnode.insert(0,'20E-7')
        self.startnode.insert(0,'0.0')
        self.stepsize.insert(0,'1E-7')
        self.lownode.grid(column=1, row=2)
        self.startnode.grid(column=1, row=0)
        self.highnode.grid(column=1, row=1)
        self.stepsize.grid(column=1, row=3)
        self.loopno=Entry(self.frame4,width=8,justify='right')
        self.loopno.grid(column=4,row=1)
        self.loopno.insert(0,'3')
        self.looplabel=Label(self.frame4, text='No. loops')
        self.looplabel.grid(column=4,row=0,sticky='e')
        
        # Manual control frame
        self.frame2=LabelFrame(self.master, text='Manual Voltage Control', pady=28, padx=10)
        self.frame2.grid(column=3, row=1, pady=10)
        self.set_limit_label1=Label(self.frame2,text='Compliance Current')
        self.set_limit_label1.grid(column=0, row=0,sticky='e')
        self.Vlimit_box=Entry(self.frame2,width=12,justify='right')
        self.Vlimit_box.grid(column=1,row=0)
        self.Vlimit_box.insert(0,'1.0')
        self.I_label1=Label(self.frame2,text='A',anchor='w')
        self.I_label1.grid(column=2,row=0)
        self.set_volts_label1=Label(self.frame2,text='Voltage')
        self.set_volts_label1.grid(column=0, row=1,sticky='e')
        self.V_box=Entry(self.frame2,width=12,justify='right')
        self.V_box.grid(column=1,row=1)
        self.V_box.insert(0,'1.00')
        self.V_label=Label(self.frame2,text='V', anchor='w')
        self.V_label.grid(column=2,row=1)
        self.V_label1=Label(self.frame2,text='Step +/-')
        self.V_label1.grid(column=0,row=2,sticky='e')
        self.V_step_box=Entry(self.frame2,width=12,justify='right')
        self.V_step_box.grid(column=1,row=2)
        self.V_step_box.insert(0,'0.1')
        self.V_label2=Label(self.frame2,text='V', anchor='w')
        self.V_label2.grid(column=2,row=2)
        self.frame3=Frame(self.frame2)
        self.frame3.grid(column=0, row=3)
        self.go_button=Button(self.frame2,text='Go', command=self.threading1, padx=10)
        self.go_button.grid(column=1, row=3, columnspan=2)
        
        self.plus_button=Button(self.frame3,text='+', command=self.plus_volt)
        self.plus_button.grid(column=1, row=0)
        self.minus_button=Button(self.frame3,text='-', command=self.minus_volt)
        self.minus_button.grid(column=0, row=0)
        self.stop_button=Button(self.frame2,text='Stop', command=self.stop_voltage)
        self.stop_button.grid(column=0, row=4, columnspan=3, sticky='ew')
        
        # Sweep or loop control
        self.frame6=LabelFrame(self.master, text='Run Sweep or Loop', pady=18)
        self.frame6.grid(column=1,row=2)
        self.sample_label=Label(self.frame6,text='Sample Name',anchor='e')
        self.sample_label.grid(column=0,row=4)
        self.sample_box=Entry(self.frame6,width=20)
        self.sample_box.grid(column=1,row=4,columnspan=2,sticky='w')
        self.button=Button(self.frame6,text='Run', command=self.threading2)
        self.button.grid(column=0,row=5, columnspan=3, sticky='ew')
        self.CheckVar1 = IntVar()
        self.check=Radiobutton(self.frame6,text='Full Loop', value=1, variable = self.CheckVar1)
        self.check1=Radiobutton(self.frame6,text='IV-Sweep', value=0, variable = self.CheckVar1)
        self.check.grid(column=0, row=0, columnspan=3)
        self.check1.grid(column=0, row=1, columnspan=3)
        self.val=self.CheckVar1.get()
        self.I_label1=Label(self.frame6,text='V', anchor='w')
        self.I_label1.grid(column=2,row=2, sticky='w')
        self.vlimit_label=Label(self.frame6,text='Voltage Limit',anchor='e')
        self.vlimit_label.grid(column=0,row=2)
        self.vlimit_box=Entry(self.frame6,width=12,justify='right')
        self.vlimit_box.grid(column=1,row=2,sticky='w')
        self.vlimit_box.insert(0,'50')
        self.ave_label=Label(self.frame6,text='Buffer size',anchor='e')
        self.ave_label.grid(column=0,row=3)
        self.ave_box=Entry(self.frame6,width=8,justify='right')
        self.ave_box.insert(0,'10')
        self.ave_box.grid(column=1,row=3,sticky='w')
        
        # Time based logging
        self.frame7=LabelFrame(self.master, text='Log Current versus time', pady=18)
        self.frame7.grid(column=2,row=2)
        self.volts_set=Entry(self.frame7,width=5)
        self.volts_set.grid(column=1, row=0)
        self.volts_label=Label(self.frame7,text='Apply Voltage',anchor='e')
        self.volts_Vlabel=Label(self.frame7,text='V',anchor='e')
        self.volts_label.grid(column=0, row=0)
        self.volts_Vlabel.grid(column=2, row=0)
        
        # Set complicance current
        self.currentmax_set=Entry(self.frame7,width=5)
        self.currentmax_set.grid(column=1, row=1)
        self.currentmax_label=Label(self.frame7,text='Current Compliance',anchor='e')
        self.currentmax_Alabel=Label(self.frame7,text='A',anchor='e')
        self.currentmax_label.grid(column=0, row=1)
        self.currentmax_Alabel.grid(column=2, row=1)
        
        #Set time interval
        self.time_inter_set=Entry(self.frame7,width=5)
        self.time_inter_set.grid(column=1, row=2)
        self.time_inter_label=Label(self.frame7,text='Approx Time Interval',anchor='e')
        self.time_inter_slabel=Label(self.frame7,text='s',anchor='e')
        self.time_inter_label.grid(column=0, row=2)
        self.time_inter_slabel.grid(column=2, row=2)
        
        #Set file name
        self.f_name=Entry(self.frame7,width=10)
        self.f_name.grid(column=1, row=4,columnspan=3)
        self.f_name_label=Label(self.frame7,text='Log name',anchor='e')
        self.f_name_label.grid(column=0, row=4)
        
        
        #Set time interval
        self.time_stop_set=Entry(self.frame7,width=5)
        self.time_stop_set.grid(column=1, row=3)
        self.time_stop_label=Label(self.frame7,text='End After',anchor='e')
        self.time_stop_slabel=Label(self.frame7,text='s',anchor='e')
        self.time_stop_label.grid(column=0, row=3)
        self.time_stop_slabel.grid(column=2, row=3)
        
        
        #Set initial values
        self.volts_set.insert(0,'5')
        self.currentmax_set.insert(0, '0.1')
        self.time_inter_set.insert(0,'1')
        self.time_stop_set.insert(0,'3600')
        
        
        #Start stop buttons
        self.timelogstart_button=Button(self.frame7,text='Start', command=self.log_time_thread)
        self.timelogstop_button=Button(self.frame7,text='Stop', command=self.stop_voltage)
        self.timelogstart_button.grid(column=0,row=5, columnspan=3,sticky='ew')   
        self.timelogstop_button.grid(column=0,row=6, columnspan=3,sticky='ew')                           
        
        self.frame8=LabelFrame(self.master, text='Update', pady=18)
        self.frame8.grid(column=3, row=2)
        self.dialogbox = Text(self.frame8, height=12, width=45, font=10, wrap=WORD)
        self.dialogbox.pack(side=LEFT, fill=BOTH, expand=True)
        # Scrollbar for the dialog box
        self.scrollbar = Scrollbar(self.frame8, command=self.dialogbox.yview)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.dialogbox.config(yscrollcommand=self.scrollbar.set)
        
        
        # Start a thread to process dialog messages
        self.workerthread = Thread(target=self.dialogue_queue_worker, daemon=True)
        self.workerthread.start()
        
        self.dialoge_queue.put('Ready')
        
        # Save Directory Selection
        self.save_dir = StringVar()
        self.save_dir.set("")  # Default to blank until user sets
        
        self.save_dir_label = Label(self.frame6, text="Save Directory:")
        self.save_dir_label.grid(column=0, row=6, sticky='e')
        self.save_dir_entry = Entry(self.frame6, textvariable=self.save_dir, width=25)
        self.save_dir_entry.grid(column=1, row=6, columnspan=2, sticky='w')
        
        self.select_dir_button = Button(self.frame6, text="Browse...", command=self.select_save_directory)
        self.select_dir_button.grid(column=0, row=7, columnspan=3, sticky='ew')
        
        # Time Log Save Directory Selection
        self.time_log_dir = StringVar()
        self.time_log_dir.set("")
        
        self.time_log_dir_label = Label(self.frame7, text="Time Log Directory:")
        self.time_log_dir_label.grid(column=0, row=7, sticky='e')
        
        self.time_log_dir_entry = Entry(self.frame7, textvariable=self.time_log_dir, width=25)
        self.time_log_dir_entry.grid(column=1, row=7, columnspan=2, sticky='w')
        
        self.select_time_dir_button = Button(self.frame7, text="Browse...", command=self.select_time_log_directory)
        self.select_time_dir_button.grid(column=0, row=8, columnspan=3, sticky='ew')
        super().__init__()
    
    def select_save_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.save_dir.set(directory)
            self.dialoge_queue.put(f"Save directory set to: {directory}")
    def select_time_log_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.time_log_dir.set(directory)
            self.dialoge_queue.put(f"Time log directory set to: {directory}")
    
    def dialogue_queue_worker(self):
        while True:
            text = self.dialoge_queue.get()
            try:
                self.dialogbox.config(state='normal')
                self.dialogbox.insert(END, text + '\n')
                self.dialogbox.yview(END)
                self.dialogbox.config(state='disabled')
            except TclError:
                # Widget has been destroyed, exit the loop/thread gracefully
                break
            self.dialoge_queue.task_done()
            
    def log_time_thread(self):
        if not self.running:
            self.running=True
            self.t3=Thread(target=self.log_I, args=(self.time_data_queue,),daemon=True)
            self.t3.start()
            self.create_a_time_plot()
   
    def threading1(self):
        t1=Thread(target=self.apply, daemon=True)
        t1.start()
    def threading2(self):
        self.running=True
        self.t2=Thread(target=self.collect_data1, args=(self.data_queue,),daemon=True)
        self.t2.start()
        self.create_a_plot()
        
    def create_a_time_plot(self):
        """Collect data from the sourcemeter and plot against time."""
    
        # Create window for real-time spectrum plot
        self.plot_win_time = Toplevel(self.master)
        self.plot_win_time.geometry("500x500")
        self.plot_win_time.title('Current -logging')
        self.plot_win_time.resizable(True, True)
    
        # Set up the figure and canvas
        fig, ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_win_time)
        self.canvas.get_tk_widget().pack()
        
        toolbar = NavigationToolbar2Tk(self.canvas, self.plot_win_time)
        toolbar.update()
        ax.set_xlabel('Time /s')
        ax.set_ylabel('Current /A')
    
        def update_time_plot():
            if not self.time_data_queue.empty():
                data = self.time_data_queue.get()
                ax.clear()
                
                ax.errorbar(data[0], data[1], yerr=data[2],color='black', marker='o')
                ax.set_xlabel('Time /s')
                ax.set_ylabel('Current /A')
                  # Recompute the data limits
                # ax.autoscale_view()  # Rescale the view
                self.canvas.draw()
                
                
            if self.running:
               
                self.plot_win_time.after(100, update_time_plot)  # Check for new data every 100ms
    
        # Start the update loop
        update_time_plot()
    def create_a_plot(self):
        """Collect data from the sourcemeter and plot it."""
    
        # Create window for real-time spectrum plot
        self.plot_win = Toplevel(self.master)
        self.plot_win.geometry("500x500")
        self.plot_win.title('I-V curve')
        self.plot_win.resizable(True, True)
    
        # Set up the figure and canvas
        fig, ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_win)
        self.canvas.get_tk_widget().pack()
        # self.line, = ax.plot([], [], 'o-')  # Initialize an empty line for plotting
        toolbar = NavigationToolbar2Tk(self.canvas, self.plot_win)
        toolbar.update()
        ax.set_xlabel('Current /A')
        ax.set_ylabel('Voltage /V')
    
        def update_plot():
            if not self.data_queue.empty():
                data = self.data_queue.get()
                ax.clear()
                
                ax.errorbar(data[0], data[1], yerr=data[2], color='black', marker='o')
                ax.set_xlabel('Current')
                ax.set_ylabel('Voltage')
                  # Recompute the data limits
                # ax.autoscale_view()  # Rescale the view
                self.canvas.draw()
                
                
            if self.running:
               
                self.plot_win.after(100, update_plot)  # Check for new data every 100ms
    
        # Start the update loop
        update_plot()
    def safe_shutdown(self):
        try:
            self.sourcemeter.shutdown()
        except KeyError as e:
            print(f"Warning: Shutdown failed due to unexpected response: {e}")
            try:
                self.sourcemeter.write("OUTP OFF")
            except Exception:
                pass

        
        

class connect_keithley:
    def __init__(self):
        self.rm = visa.ResourceManager()
     
# print('Device List is',rm.list_resources())
    def find(self):
        j=0
        found=False
        self.devicelist=self.rm.list_resources()
        
        print(self.devicelist)
        while j<len(self.devicelist) and not found:
            
            try:
                print('Attemping to connect try=', j)
                self.adapter=VISAAdapter(self.devicelist[j], timeout=10000)
                sm = Keithley2400(self.adapter)
                check=sm.id
                
                if check[0:8]=='KEITHLEY':
                    print('Connection Established')
                    sourcemeter=sm
                    found=True
                    break
                else:
                    j+=1
                    
            except:
                print('Not the Keithley')
                j+=1
                time.sleep(1)
                
                    
                    
        if found:
            return True, sourcemeter
        else:
            print('Keithley 2400 not found')
            return False, None
                
            
if __name__=='__main__':   
    warnings.filterwarnings("ignore", category=UserWarning, module='pyvisa_py.tcpip')
    
    
            
    sourcemeter=None         
    connection=connect_keithley()
    query, sourcemeter=connection.find()
    
    query=True
    if query:
        root=Tk()
        
        app=App(root, sourcemeter)
        def on_closing():
            if messagebox.askokcancel("Quit", "Do you want to quit?"):
                try:
                    if app.sourcemeter is not None:
                        app.sourcemeter.shutdown()
                        app.dialoge_queue.put("Keithley shut down.")
                        app.dialoge_queue.put(None)
                except Exception as e:
                    print(f"Error during shutdown: {e}")
                finally:
                    root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_closing)
        mainloop()
        
        

        # sourcemeter.shutdown()
