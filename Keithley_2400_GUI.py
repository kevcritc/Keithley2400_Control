#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 18 18:23:27 2022

@author: phykc
"""
from tkinter import *
from queue import Queue
from threading import *
from time import sleep
import numpy as np
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  NavigationToolbar2Tk)
from pymeasure.instruments.keithley import Keithley2400
from pymeasure.adapters import VISAAdapter
import pyvisa as visa

class IVsweep():
    '''Connect and configure the instrument'''
    # Either uses loop values or V1 to V2  method.
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
        currents = np.zeros_like(self.voltages)
        currentsstd = np.zeros_like(self.voltages)
        i=0
        # Loop through each current point, measure and record the voltage
        while i<len(self.voltages) and self.sweep:
            sourcemeter.source_voltage=self.voltages[i]
            sleep(0.1)
            currarray=np.array(sourcemeter.current)
            # Record the average and standard deviation
            currents[i] = np.mean(currarray)
            currentsstd[i] =np.std(currarray)
            i+=1

        sourcemeter.shutdown()    
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
        # plot the data
        #plt.xlabel('Voltage / V')
        #plt.ylabel('Current, A')
        #plt.errorbar(self.voltages,currents,yerr=currentsstd, color='black')
        #plt.show()
#%%
class IVsweep4probe():
    '''Connect and configure the instrument for four probe'''
    # Either uses loop values or V1 to V2  method.
    def collect_data1(self, queue):
        self.running=True
        self.sweep=True
        self.queue=queue
        self.data_points = int(self.step_box.get())
        self.averages = int(self.ave_box.get())
        self.max_volt = float(self.Vlimit_box.get())
        if abs(self.max_volt)>199:
            self.max_current=199
        self.startI=float(self.start_box.get())
        self.endI=float(self.end_box.get())
        self.prename=self.sample_box.get()
        self.val=self.CheckVar1.get()
        if self.startI>self.endI:
            self.startI, self.endI=self.endI, self.startI
        sourcemeter.reset()
        sourcemeter.use_front_terminals()
        sourcemeter.apply_current()
        sourcemeter.compliance_voltage=self.max_volt
        sourcemeter.measure_voltage(voltage=self.max_volt, auto_range=True)
        sleep(0.1) # wait here to give the instrument time to react
        sourcemeter.config_buffer(self.averages)
        sourcemeter.enable_source()
        sleep(0.1)
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
        # Loop through each voltage point, measure and record the voltage
        while i<len(self.amps) and self.sweep:
            sourcemeter.source_current=self.amps[i]
            sleep(0.1)
            voltsarray=np.array(sourcemeter.voltage)
            # Record the average and standard deviation
            volts[i] = np.mean(voltsarray)
            voltsstd[i] =np.std(voltsarray)
            self.data_queue.put([self.amps[:i], volts[:i], voltsstd[:i]])   
            i+=1
        sourcemeter.shutdown()    
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
        full_filename=self.sample_box.get()+filename
        data.to_csv(full_filename)
        self.running=False
        
# Class for setting voltage manually and steping.
class Set_voltage:
    def man_V(self):
        self.max_current = float(self.Vlimit_box.get())
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
        
class App(IVsweep4probe,Set_voltage):
    def __init__(self,master):
        self.statecol=NORMAL
        self.master=master
        self.master.title('Keithley 2400 4-Probe Control')
        self.data_queue=Queue()
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
        self.frame2=LabelFrame(self.master, text='Compliance Voltage and Applying Manual Voltage Setting', pady=28, padx=10)
        self.frame2.grid(column=3, row=1, pady=10)
        self.set_limit_label1=Label(self.frame2,text='Compliance Voltage')
        self.set_limit_label1.grid(column=0, row=0,sticky='e')
        self.Vlimit_box=Entry(self.frame2,width=12,justify='right')
        self.Vlimit_box.grid(column=1,row=0)
        self.Vlimit_box.insert(0,'10')
        self.I_label1=Label(self.frame2,text='V',anchor='w')
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
        self.frame6.grid(column=4,row=1)
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
        self.I_label1=Label(self.frame6,text='A', anchor='w')
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
        
        
        super().__init__()
   
    def threading1(self):
        t1=Thread(target=self.apply, daemon=True)
        t1.start()
    def threading2(self):
        self.running=True
        self.t2=Thread(target=self.collect_data1, args=(self.data_queue,),daemon=True)
        self.t2.start()
        self.create_a_plot()
        

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
                sleep(1)
                
                    
                    
        if found:
            return True, sourcemeter
        else:
            print('Keithley 2400 not found')
            return False, None
                
            
if __name__=='__main__':            
    connection=connect_keithley()
    query, sourcemeter=connection.find()
    # query=True
    if query:
        root=Tk()
        
        app=App(root)
        
        mainloop()
        
        sourcemeter.shutdown()
        print('The Keithley is switched to off')
