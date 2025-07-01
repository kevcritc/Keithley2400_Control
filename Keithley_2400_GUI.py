#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 18 18:23:27 2022

@author: phykc
"""
from tkinter import *
from queue import Queue
from threading import *
import logging
import time
import numpy as np
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  NavigationToolbar2Tk)
from pymeasure.instruments.keithley import Keithley2400
from pymeasure.adapters import VISAAdapter
import pyvisa as visa
from pyvisa.constants import Parity, StopBits
from tkinter import messagebox,filedialog
import os
import warnings
import json
import re
from wakepy import keep



class IVsweep():
    def collect_data(self):
        self.sourcemeter.set_timeout(30000)
        self.dialogue_queue.put('Setting up measurement')
        self.running = True
        self.sweep = True

        # Get values from the new Voltage Sweep frame
        self.data_points = int(self.vsweep_points.get())
        self.averages = int(self.vsweep_buffer.get())
        self.startV = float(self.vsweep_start.get())
        self.endV = float(self.vsweep_end.get())
        self.save_path = self.vsweep_save_dir.get()
        self.max_current = float(self.vsweep_compliance.get())

        if self.startV > self.endV:
            self.startV, self.endV = self.endV, self.startV
        self.sourcemeter.reset()  
        
        
        time.sleep(0.1)
        self.sourcemeter.use_front_terminals()
        time.sleep(0.1)
        if self.vsweep_4w_var.get() == 1:
            self.sourcemeter.adapter.write("SYST:RSEN ON")
            self.dialogue_queue.put("4-wire sensing enabled (voltage sweep).")
        else:
            self.sourcemeter.adapter.write("SYST:RSEN OFF")
            self.dialogue_queue.put("4-wire sensing disabled (voltage sweep).")
        time.sleep(0.1)
        self.sourcemeter.apply_voltage(voltage_range=None, compliance_current=self.max_current)
        
        time.sleep(0.1)
        self.sourcemeter.config_buffer(int(self.averages),0)
        time.sleep(0.1)
        self.sourcemeter.enable_source()
        time.sleep(0.1)
        # --- Current ---
        selected_i_range = self.current_range_var.get()
        if selected_i_range == "auto":
            self.sourcemeter.measure_current(auto_range=True)
        else:
            self.sourcemeter.measure_current(current=float(selected_i_range), auto_range=False)

        
        self.voltages = np.linspace(self.startV, self.endV, num=self.data_points)
        self.running=True
        self.run_volts()
        self.set_controls_state(NORMAL)
        self.running=False

    def run_volts(self):
        with keep.running():
            self.dialogue_queue.put('Measuring')
    
            currents = np.zeros_like(self.voltages)
            currentsstd = np.zeros_like(self.voltages)
            i = 0
    
            while i < len(self.voltages) and self.running:
                self.sourcemeter.source_voltage = self.voltages[i]
                time.sleep(0.1)
                
                currents_only=self.sourcemeter.current
                currents[i] = np.mean(currents_only)
                currentsstd[i] = np.std(currents_only)
                self.data_queue.put([self.voltages[:i], currents[:i], currentsstd[:i]])  
                i += 1
    
            self.dialogue_queue.put('Saving data')
            self.sourcemeter.shutdown()
            raw_name = self.vsweep_sample.get()
            safe_name = self.sanitize_filename(raw_name)
            name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S.csv")
            full_filename = os.path.join(self.save_path, safe_name + '_' + name)
    
            data = pd.DataFrame({
                'Voltage (V)': self.voltages,
                'Current (A)': currents,
                'Current std (A)': currentsstd
            })
            
        
            df=pd.DataFrame(data)
            df.to_csv(full_filename)
            # Define the JSON settings filename
            settings_filename = full_filename.replace(".csv", "_settings.json")
            
            # Save current settings using your existing method
            with open(settings_filename, 'w') as f:
                json.dump(self.get_settings_dict(), f, indent=4)
    
    
            self.dialogue_queue.put(f'Data saved to {full_filename}')
            self.dialogue_queue.put(f"Settings saved to {settings_filename}")


        

class IVsweep4probe():
    # Connect and configure the instrument might need to edit
    # Either uses loop values or V1 to V2  method.
    def collect_data1(self, queue):
        with keep.running():
            try:
                self.dialogue_queue.put('Setting up measurement')
                self.running=True
                self.sweep=True
                self.queue=queue
                self.data_points = int(self.step_box.get())
                self.averages = int(self.ave_box.get())
                self.max_volt = float(self.vlimit_box.get())
                if abs(self.max_volt)>199:
                    self.max_volt=199
                self.dialogue_queue.put(f'Max voltage allowed is {self.max_volt}')
                self.startI=float(self.start_box.get())
                self.endI=float(self.end_box.get())
                self.prename=self.sample_box.get()
                self.val=self.CheckVar1.get()
                if self.startI>self.endI:
                    self.startI, self.endI=self.endI, self.startI
                self.sourcemeter.reset()
                self.sourcemeter.use_front_terminals()
                if self.four_wire_var.get() == 1:
                    self.sourcemeter.adapter.write("SYST:RSEN ON")
                    self.dialogue_queue.put("4-wire sensing enabled.")
                else:
                    self.sourcemeter.adapter.write("SYST:RSEN OFF")
                    self.dialogue_queue.put("4-wire sensing disabled.")
                time.sleep(0.1)
                self.sourcemeter.apply_current()
                self.sourcemeter.compliance_voltage=self.max_volt
                # --- Voltage ---
                selected_v_range = self.voltage_range_var.get()
                if selected_v_range == "auto":
                    self.sourcemeter.measure_voltage(auto_range=True)
                else:
                    self.sourcemeter.measure_voltage(voltage=float(selected_v_range), auto_range=False)
        
                time.sleep(0.1) # wait here to give the instrument time to react
                self.sourcemeter.config_buffer(self.averages)
                self.sourcemeter.enable_source()
                time.sleep(0.1)
                self.dialogue_queue.put('Sourcemeter is ready')
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
                self.set_controls_state(NORMAL)
            except Exception as e:
                self.dialogue_queue.put(f"Error during measurement: {e}")
            finally:
                self.set_controls_state(NORMAL)
                self.running = False
        
    def run_amps(self):
        with keep.running():
            volts = np.zeros_like(self.amps)
            voltsstd = np.zeros_like(self.amps)
            i=0
            self.dialogue_queue.put('Running measurement')
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
            self.dialogue_queue.put('Stopping measurement')
            # Save the data columns in a CSV file
            data = pd.DataFrame({
                
                'Current (A)': self.amps,
                'Voltage mean (V)': volts,
                'Voltage std (A)':voltsstd,
                
            })
            # create a file name usine time date save it to the py code path.
            name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S.csv")
            raw_name = self.sample_box.get()
            save_path = self.save_dir.get()
            safe_name = self.sanitize_filename(raw_name)
            full_filename = os.path.join(save_path, safe_name + '_' + name)
        
            df=pd.DataFrame(data)
            df.to_csv(full_filename)
            self.dialogue_queue.put(f'Data saved to{full_filename}')
            # Define the JSON settings filename
            settings_filename = full_filename.replace(".csv", "_settings.json")
            
            # Save current settings using your existing method
            with open(settings_filename, 'w') as f:
                json.dump(self.get_settings_dict(), f, indent=4)
            self.dialogue_queue.put(f'Settings saved to{settings_filename}')
            self.running=False
        
        

# Set up threading for the manual control part


# Class for setting voltage manually and steping.
class Set_voltage:
    def man_V(self):
        self.dialogue_queue.put('Manual Voltage Initalising')
        self.max_current = float(self.Vlimit_box.get())
        if self.max_current>1.0:
            self.max_current=1.0
        self.setV=float(self.V_box.get())
        self.running=True
        self.sourcemeter.use_front_terminals()
        if self.four_wire_manual.get() == 1:
            self.sourcemeter.adapter.write("SYST:RSEN ON")
            self.dialogue_queue.put("4-wire sensing enabled (manual voltage).")
        else:
            self.sourcemeter.adapter.write("SYST:RSEN OFF")
            self.dialogue_queue.put("4-wire sensing disabled (manual voltage).")
        self.sourcemeter.apply_voltage()
        selected_i_range = self.current_range_var.get()
        if selected_i_range == "auto":
            self.sourcemeter.measure_current(auto_range=True)
        else:
            self.sourcemeter.measure_current(current=float(selected_i_range), auto_range=False)
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
    
    # 1) Clear any existing handlers so basicConfig will take effect
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    
    # 2) Build your timestamped filename next to this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    now      = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logfile  = os.path.join(base_dir, f"testlog_{now}.txt")
    
    # 3) Configure logging to write *only* to that file
    logging.basicConfig(
        filename=logfile,
        filemode="a",              # append; use "w" to overwrite each run
        level=logging.DEBUG,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # 4) Grab your module logger
    logger = logging.getLogger(__name__)
    def log_I(self, time_data_queue, resource):
        self.resource=resource
        self.dialogue_queue.put('Initalising a time log')
        self.logger.debug("Initialising",self.logfile)
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
        self.dialogue_queue.put('Front terminals set')
        
        if self.four_wire_time.get() == 1:
            self.sourcemeter.adapter.write("SYST:RSEN ON")
            self.dialogue_queue.put("4-wire sensing enabled (time log).")
        else:
            self.sourcemeter.adapter.write("SYST:RSEN OFF")
            self.dialogue_queue.put("4-wire sensing disabled (time log).")
        time.sleep(0.1)  
        self.sourcemeter.apply_voltage()
       
    
        time.sleep(0.1) 
        self.sourcemeter.source_mode = 'voltage'
        time.sleep(0.1) 
        selected_i_range = self.current_range_var.get()
        if selected_i_range == "auto":
            self.sourcemeter.measure_current(auto_range=True)
        else:
            self.sourcemeter.measure_current(nplc=0.01, current=float(selected_i_range), auto_range=False)
        time.sleep(0.1) 
        self.sourcemeter.compliance_current=self.max_current
        self.buffer_size = int(self.time_buffer_set.get())
        self.sourcemeter.config_buffer(self.buffer_size)
        time.sleep(0.1) # wait here to give the instrument time to react
        self.dialogue_queue.put('Starting..')
        self.maxtime=int(self.time_stop_set.get())
        
        self.sourcemeter.sample_continuously()
        
        self.sourcemeter.source_voltage=self.setV
        self.sourcemeter.enable_source()
        
        time.sleep(0.1)
        start_time = time.time()
        interval=float(self.time_inter_set.get())
        last_read    = start_time
        # fudge to get it 
        inter_mod=interval-0.7275
        if inter_mod<0:
            inter_mod=0.0
            self.dialogue_queue.put('The sampling takes about 0.7s - it is possible to reduce but will require some changes')
            
        with keep.running():
            while self.running:
                try:
                    # Drain the instrument’s buffer
                    current_samples = np.array(self.sourcemeter.current)
                    self.currentlog.append(np.mean(current_samples))
                except visa.VisaIOError as e:
                    # catch the exact timeout code
                    if e.error_code == visa.constants.VI_ERROR_TMO:
                        self.dialogue_queue.put("Timeout -> likely woke from sleep")
                        self._reconnect()
                        last_read = time.time()
                        continue
                    else:
                        self.dialogue_queue.put(f"VISA error: {e}")
                        break
                
                try:
                    self.currentlogstd.append(np.std(current_samples) / np.sqrt(len(current_samples)))
                except:
                    self.currentlogstd.append(0)
                if self.sourcemeter.is_buffer_full():
                    self.sourcemeter.reset_buffer()
                    self.dialogue_queue.put('Resetting buffer')
                    self.logger.debug('Resetting buffer')
                errors=self.sourcemeter.check_errors()  
                if len(errors)>0:
                    
                    self.logger.debug(f'Errors {errors}')
                current_time = time.time()
                last_read = current_time
                self.timelog.append(current_time-start_time)
                time.sleep(inter_mod)
                if current_time-start_time>self.maxtime:
                    self.stop_voltage()
                data=[self.timelog,self.currentlog,self.currentlogstd]
                self.time_data_queue.put(data)
            self.dialogue_queue.put('Stopped')
            self.set_controls_state(NORMAL)
            self.save_data()
    def _reconnect(self):
        """Close and reopen the VISA session & re-apply all settings."""
        self.dialogue_queue.put("Reconnecting after sleep…")
        # 1) tear down
        try:
            self.sourcemeter.disable_source()
        except: pass
        try:
            self.sourcemeter.adapter.session.close()
        except: pass

        # 2) rebuild RM + adapter + sm
        self.rm = visa.ResourceManager()
        adapter = VISAAdapter(self.resource, timeout=2000)
        self.sourcemeter = Keithley2400(adapter)

        # 3) re-apply your config (4-wire, buffer, sample mode, voltage, ranges…)
        self.sourcemeter.use_front_terminals()
        if self.four_wire_time.get():
            adapter.write("SYST:RSEN ON")
        else:
            adapter.write("SYST:RSEN OFF")
        self.sourcemeter.apply_voltage()
        self.sourcemeter.source_mode = 'voltage'
        self.sourcemeter.compliance_current = self.max_current
        self.sourcemeter.config_buffer(self.buffer_size)
        self.sourcemeter.sample_continuously()
        self.sourcemeter.source_voltage = self.setV
        self.sourcemeter.enable_source()
        time.sleep(0.1)
        self.dialogue_queue.put("Reconnected and configured.")
        
    def save_data(self):
        self.dialogue_queue.put('Saving data')
        data = pd.DataFrame({
            
            'Time (s)': self.timelog,
            'Current (A)': self.currentlog,
            'Current error (A)': self.currentlogstd
            
        })
        # create a file name usine time date save it to the py code path.
        name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S.csv")
        raw_name = self.f_name.get()
        safe_name = self.sanitize_filename(raw_name)
        
        
        save_path = self.time_log_dir.get()
        if not save_path:
            self.dialogue_queue.put("No time log directory selected — using default path.")
            save_path = os.getcwd()
        
        full_filename = os.path.join(save_path, safe_name + '_' + name)
        
        data.to_csv(full_filename)
        self.dialogue_queue.put(f'Saved {full_filename}')
        # Define the JSON settings filename
        settings_filename = full_filename.replace(".csv", "_settings.json")
        
        # Save current settings using your existing method
        with open(settings_filename, 'w') as f:
            json.dump(self.get_settings_dict(), f, indent=4)
        self.dialogue_queue.put(f'Settings saved to {settings_filename}')
        
        
        
            
            
    

class App(IVsweep, IVsweep4probe,Set_voltage, Log_current):
    
    def __init__(self,master, sourcemeter):
        self.resource=None
        self.connection=None
        self.sourcemeter=sourcemeter
        self.statecol=NORMAL
        self.master=master
        self.master.title('Keithley 2400 Series Control Panel - K Critchley')
        
        self.data_queue=Queue()
        self.time_data_queue=Queue()
        self.dialogue_queue = Queue()
        
        self.running=False
        
        # Inside frame1 is the IV selection
        self.frame1=LabelFrame(self.master, text='Current Source: I-V Sweep Settings', padx=10, pady=56)
        self.frame1.grid(column=1, row=0, padx=10, pady=10, sticky="n")
        self.I_label=Label(self.frame1,text='A', anchor='w')
        self.I_label.grid(column=2,row=0)
        self.start_label=Label(self.frame1,text='Start I (A)', anchor='e')
        self.start_label.grid(column=0,row=0,sticky='e')
        self.start_box=Entry(self.frame1,width=6,justify='right')
        self.start_box.grid(column=1,row=0)
        self.start_box.insert(0,'0.0')
        self.I_label=Label(self.frame1,text='A', anchor='w')
        self.I_label.grid(column=2,row=1)
        self.end_label=Label(self.frame1,text='End I (A)',anchor='e')
        self.end_label.grid(column=0,row=1,sticky='e')
        self.end_box=Entry(self.frame1,width=6,justify='right')
        self.end_box.insert(0,'1E-6')
        self.end_box.grid(column=1,row=1)
        self.step_label=Label(self.frame1,text='No. Data points',anchor='e')
        self.step_label.grid(column=0,row=2,sticky='e')
        self.step_box=Entry(self.frame1,width=6,justify='right')
        self.step_box.grid(column=1,row=2)
        self.step_box.insert(0,'20')
        
        
        # Loop control
        self.frame4=LabelFrame(self.master, text='Current Source: Full Loop Control', padx=10, pady=42)
        self.frame4.grid(column=2,row=0,  padx=10, pady=10, sticky="n")
        self.n1_label=Label(self.frame4,text='I_min (A)')
        self.n2_label=Label(self.frame4,text='I start (A)')
        self.n3_label=Label(self.frame4,text='I max (A)')
        self.n4_label=Label(self.frame4,text='I step (A)')
        self.n1_label.grid(column=0, row=2, sticky='e')
        self.n2_label.grid(column=0, row=0,sticky='e')
        self.n3_label.grid(column=0, row=1,sticky='e')
        self.n4_label.grid(column=0, row=3, sticky='e')
        self.lownode=Entry(self.frame4, width=6, justify='right')
        self.highnode=Entry(self.frame4, width=6, justify='right')
        self.startnode=Entry(self.frame4, width=6, justify='right')
        self.stepsize=Entry(self.frame4, width=6, justify='right')
        self.lownode.insert(0,'-20E-7')
        self.highnode.insert(0,'20E-7')
        self.startnode.insert(0,'0.0')
        self.stepsize.insert(0,'1E-7')
        self.lownode.grid(column=1, row=2)
        self.startnode.grid(column=1, row=0)
        self.highnode.grid(column=1, row=1)
        self.stepsize.grid(column=1, row=3)
        self.loopno=Entry(self.frame4,width=3,justify='right')
        self.loopno.grid(column=4,row=1)
        self.loopno.insert(0,'3')
        self.looplabel=Label(self.frame4, text='No. loops')
        self.looplabel.grid(column=4,row=0,sticky='e')
        
        # Manual control frame
        self.frame2=LabelFrame(self.master, text='Manual Voltage Source Control', pady=28, padx=10)
        self.frame2.grid(column=3, row=0,  padx=10, pady=10, sticky="n")
        self.four_wire_manual = IntVar(value=0)
        self.manual_4w_check = Checkbutton(
            self.frame2,
            text="Enable 4-wire sensing",
            variable=self.four_wire_manual
            )
        self.manual_4w_check.grid(column=0, row=6, columnspan=2, sticky='w')
        self.set_limit_label1=Label(self.frame2,text='Compliance Current (A)')
        self.set_limit_label1.grid(column=0, row=0,sticky='e')
        self.Vlimit_box=Entry(self.frame2,width=6,justify='right')
        self.Vlimit_box.grid(column=1,row=0)
        self.Vlimit_box.insert(0,'1.0')
        
        self.set_volts_label1=Label(self.frame2,text='Voltage (V)')
        self.set_volts_label1.grid(column=0, row=1,sticky='e')
        self.V_box=Entry(self.frame2,width=6,justify='right')
        self.V_box.grid(column=1,row=1)
        self.V_box.insert(0,'1.00')
        
        self.V_label1=Label(self.frame2,text='Step +/- (V)')
        self.V_label1.grid(column=0,row=2,sticky='e')
        self.V_step_box=Entry(self.frame2,width=6,justify='right')
        self.V_step_box.grid(column=1,row=2)
        self.V_step_box.insert(0,'0.1')
        
        self.frame3=Frame(self.frame2)
        self.frame3.grid(column=0, row=3)
        self.go_button=Button(self.frame2,text='Apply', command=self.threading1, padx=10)
        self.go_button.grid(column=1, row=3, columnspan=2)
        
        self.plus_button=Button(self.frame3,text='+', command=self.plus_volt)
        self.plus_button.grid(column=1, row=0)
        self.minus_button=Button(self.frame3,text='-', command=self.minus_volt)
        self.minus_button.grid(column=0, row=0)
        self.stop_button=Button(self.frame2,text='Stop', command=self.stop_voltage)
        self.stop_button.grid(column=0, row=4, columnspan=3, sticky='ew')
        
        # Sweep or loop control
        self.frame6=LabelFrame(self.master, text='Source Current:Run Sweep or Loop ', pady=18)
        self.frame6.grid(column=1,row=1, padx=10, pady=10, sticky="n")
        self.four_wire_var = IntVar(value=1)
        self.four_wire_check = Checkbutton(self.frame6, text='Enable 4-wire sensing', variable=self.four_wire_var)
        self.four_wire_check.grid(column=0, row=9, columnspan=3, sticky='w')
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
        self.sweep_stop_button = Button(self.frame6, text='Stop', command=self.stop_voltage)
        self.sweep_stop_button.grid(column=0, row=6, columnspan=3, sticky='ew', pady=(2, 5))
        self.sweep_stop_button.config(state=DISABLED)
        
        self.vlimit_label=Label(self.frame6,text='Voltage Limit (V)',anchor='e')
        self.vlimit_label.grid(column=0,row=2)
        self.vlimit_box=Entry(self.frame6,width=6,justify='right')
        self.vlimit_box.grid(column=1,row=2,sticky='w')
        self.vlimit_box.insert(0,'50')
        self.ave_label=Label(self.frame6,text='Buffer size',anchor='e')
        self.ave_label.grid(column=0,row=3)
        self.ave_box=Entry(self.frame6,width=6,justify='right')
        self.ave_box.insert(0,'10')
        self.ave_box.grid(column=1,row=3,sticky='w')
        # Save Directory Selection
        self.save_dir = StringVar()
        self.save_dir.set("")  # Default to blank until user sets
        
        self.save_dir_label = Label(self.frame6, text="Save Directory:")
        self.save_dir_label.grid(column=0, row=7, sticky='e')
        self.save_dir_entry = Entry(self.frame6, textvariable=self.save_dir, width=25)
        self.save_dir_entry.grid(column=1, row=7, columnspan=2, sticky='w')
        
        self.select_dir_button = Button(self.frame6, text="Browse...", command=self.select_save_directory)
        self.select_dir_button.grid(column=0, row=8, columnspan=3, sticky='ew')
        
        # Time based logging
        self.frame7=LabelFrame(self.master, text='Voltage Source: Log Current over time', pady=18)
        self.frame7.grid(column=2,row=1, padx=10, pady=8, sticky="n")
        self.four_wire_time = IntVar(value=0)
        self.time_4w_check = Checkbutton(
            self.frame7,
            text="Enable 4-wire sensing",
            variable=self.four_wire_time
        )
        self.time_4w_check.grid(column=0, row=10, columnspan=3, sticky='w')
        self.volts_set=Entry(self.frame7,width=6,justify='right')
        self.volts_set.grid(column=1, row=0)
        self.volts_label=Label(self.frame7,text='Apply Voltage (V)',anchor='e')
        self.volts_label.grid(column=0, row=0)
        # Set complicance current
        self.currentmax_set=Entry(self.frame7,width=6,justify='right')
        self.currentmax_set.grid(column=1, row=1)
        self.currentmax_label=Label(self.frame7,text='Current Compliance (A)',anchor='e')
        
        self.currentmax_label.grid(column=0, row=1)
       
        
        #Set time interval
        self.time_inter_set=Entry(self.frame7,width=6,justify='right')
        self.time_inter_set.grid(column=1, row=2)
        self.time_inter_label=Label(self.frame7,text='Approx Time Interval (s)',anchor='e')
        
        self.time_inter_label.grid(column=0, row=2)
       
        
        #Set file name
        self.f_name=Entry(self.frame7,width=25)
        self.f_name.grid(column=1, row=5,columnspan=3)
        self.f_name_label=Label(self.frame7,text='Log name',anchor='e')
        self.f_name_label.grid(column=0, row=5)
        
        
        #Set time interval
        self.time_stop_set=Entry(self.frame7,width=6,justify='right')
        self.time_stop_set.grid(column=1, row=3)
        self.time_stop_label=Label(self.frame7,text='End After (s)',anchor='e')
        
        self.time_stop_label.grid(column=0, row=3)
        #Set initial values
        self.volts_set.insert(0,'5')
        self.currentmax_set.insert(0, '0.1')
        self.time_inter_set.insert(0,'1')
        self.time_stop_set.insert(0,'3600')
        
        
        #Start stop buttons
        self.timelogstart_button=Button(self.frame7,text='Start', command=self.log_time_thread)
        self.timelogstop_button=Button(self.frame7,text='Stop', command=self.stop_voltage)
        self.timelogstart_button.grid(column=0,row=6, columnspan=3,sticky='ew')   
        self.timelogstop_button.grid(column=0,row=7, columnspan=3,sticky='ew')   
        
        #Frame for voltage sweep
        
        self.frame_voltage_sweep = LabelFrame(self.master, text='Voltage Source Sweep', pady=18, padx=10)
        self.frame_voltage_sweep.grid(column=3, row=1, padx=10, pady=10, sticky="n")
        # Voltage Start
        Label(self.frame_voltage_sweep, text='Start V:').grid(row=0, column=0, sticky='e')
        self.vsweep_start = Entry(self.frame_voltage_sweep, width=6, justify='right')
        self.vsweep_start.grid(row=0, column=1)
        self.vsweep_start.insert(0, '0.0')
        # Voltage End
        Label(self.frame_voltage_sweep, text='End V:').grid(row=1, column=0, sticky='e')
        self.vsweep_end = Entry(self.frame_voltage_sweep, width=6, justify='right')
        self.vsweep_end.grid(row=1, column=1)
        self.vsweep_end.insert(0, '10.0')
        
        # Number of Points
        Label(self.frame_voltage_sweep, text='Data Points:').grid(row=2, column=0, sticky='e')
        self.vsweep_points = Entry(self.frame_voltage_sweep, width=6, justify='right')
        self.vsweep_points.grid(row=2, column=1)
        self.vsweep_points.insert(0, '20')
        
        # Buffer Size
        Label(self.frame_voltage_sweep, text='Buffer Size:').grid(row=3, column=0, sticky='e')
        self.vsweep_buffer = Entry(self.frame_voltage_sweep, width=6, justify='right')
        self.vsweep_buffer.grid(row=3, column=1)
        self.vsweep_buffer.insert(0, '10')
        
        # Compliance Current
        Label(self.frame_voltage_sweep, text='Compliance I (A):').grid(row=4, column=0, sticky='e')
        self.vsweep_compliance = Entry(self.frame_voltage_sweep, width=6, justify='right')
        self.vsweep_compliance.grid(row=4, column=1)
        self.vsweep_compliance.insert(0, '0.1')
        
        # Sample Name
        Label(self.frame_voltage_sweep, text='Sample Name:').grid(row=5, column=0, sticky='e')
        self.vsweep_sample = Entry(self.frame_voltage_sweep, width=25)
        self.vsweep_sample.grid(row=5, column=1, columnspan=2)
        
        
        # Save Directory
        Label(self.frame_voltage_sweep, text='Save Directory:').grid(row=6, column=0, sticky='e')
        self.vsweep_save_dir = StringVar()
        self.vsweep_save_entry = Entry(self.frame_voltage_sweep, textvariable=self.vsweep_save_dir, width=25)
        self.vsweep_save_entry.grid(row=6, column=1, columnspan=2)
        
        # Browse button
        self.vsweep_browse = Button(self.frame_voltage_sweep, text='Browse...',
                                    command=lambda: self.vsweep_save_dir.set(filedialog.askdirectory()))
        self.vsweep_browse.grid(row=7, column=0, columnspan=3, sticky='ew')
        
        # 4-wire sense checkbox
        self.vsweep_4w_var = IntVar(value=0)
        self.vsweep_4w_check = Checkbutton(self.frame_voltage_sweep,
                                           text="Enable 4-wire sensing",
                                           variable=self.vsweep_4w_var)
        self.vsweep_4w_check.grid(row=12, column=0, columnspan=3, sticky='w', pady=(5, 0))
        
        # Run and Stop Buttons (adjusted to correct rows)
        self.vsweep_run = Button(self.frame_voltage_sweep, text='Run', command=self.vsweep_run_thread)
        self.vsweep_run.grid(row=9, column=0, columnspan=3, sticky='ew')
        
        self.vsweep_stop = Button(self.frame_voltage_sweep, text='Stop', command=self.stop_voltage)
        self.vsweep_stop.grid(row=10, column=0, columnspan=3, sticky='ew')
        
    
                                
        
        self.frame8=LabelFrame(self.master, text='Update', pady=18)
        self.frame8.grid(column=1, row=2, padx=10, columnspan=3, pady=10, sticky="n")
        self.dialogbox = Text(self.frame8, height=6, width=120, font=10, wrap=WORD)
        self.dialogbox.pack(side=LEFT, fill=BOTH, expand=True)
        # Scrollbar for the dialog box
        self.scrollbar = Scrollbar(self.frame8, command=self.dialogbox.yview)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.dialogbox.config(yscrollcommand=self.scrollbar.set)
        
        # Buffer Size Entry
        self.time_buffer_label = Label(self.frame7, text="Buffer Size:")
        self.time_buffer_label.grid(column=0, row=4, sticky='e')
        
        self.time_buffer_set = Entry(self.frame7, width=6, justify='right')
        self.time_buffer_set.grid(column=1, row=4)
        self.time_buffer_set.insert(0, '10')  # default value
        
        # connect to Keighley
        
        self.frame9=LabelFrame(self.master, text='Settings', pady=18)
        self.frame9.grid(column=0, row=0, padx=10, pady=10, sticky="n")
        self.connectbutton=Button(self.frame9,text="Connect to Keithley", command=self.make_connection)
        self.connectbutton.pack()
        self.disconnectbutton=Button(self.frame9,text="Disconnect Keithley", command=self.disconnect)
        
        self.connection_status = Label(self.frame9, text="Not Connected", fg="red")
        self.connection_status.pack()
        self.disconnectbutton.pack()
        
        
        # Enble setting the sensitivity
        self.range_frame = LabelFrame(self.master, text='Voltage and Current Sensitivity Range', pady=10, padx=10)
        self.range_frame.grid(column=0, row=1, padx=10, pady=10, sticky='n')
        
        # Variables to hold the selected range
        self.voltage_range_var = StringVar(value="auto")
        self.current_range_var = StringVar(value="auto")
        
        # Voltage Range Selection
        Label(self.range_frame, text="Voltage Range:").grid(row=0, column=0, sticky='w')
        voltage_ranges_sen = [("Auto", "auto"), ("0.2 V", "0.2"), ("2 V", "2"), ("20 V", "20"), ("200 V", "200")]
        for i, (label, val) in enumerate(voltage_ranges_sen):
            Radiobutton(self.range_frame, text=label, variable=self.voltage_range_var, value=val).grid(row=i+1, column=0, sticky='w')
        
        # Current Range Selection
        Label(self.range_frame, text="Current Range:").grid(row=0, column=1, sticky='w', padx=(20, 0))
        current_ranges_sen = [("Auto", "auto"), ("1 µA", "1e-6"), ("10 µA", "1e-5"), ("100 µA", "1e-4"),
                          ("1 mA", "1e-3"), ("10 mA", "1e-2"), ("100 mA", "1e-1"), ("1 A", "1.0")]
        for i, (label, val) in enumerate(current_ranges_sen):
            Radiobutton(self.range_frame, text=label, variable=self.current_range_var, value=val).grid(row=i+1, column=1, sticky='w', padx=(20, 0))

        # Start a thread to process dialog messages
        self.workerthread = Thread(target=self.dialogue_queue_worker, daemon=True)
        self.workerthread.start()
        
        
        
        
        
        # Time Log Save Directory Selection
        self.time_log_dir = StringVar()
        self.time_log_dir.set("")
        
        self.time_log_dir_label = Label(self.frame7, text="Time Log Directory:")
        self.time_log_dir_label.grid(column=0, row=8, sticky='e')
        
        self.time_log_dir_entry = Entry(self.frame7, textvariable=self.time_log_dir, width=25)
        self.time_log_dir_entry.grid(column=1, row=8, columnspan=2, sticky='w')
        
        self.select_time_dir_button = Button(self.frame7, text="Browse...", command=self.select_time_log_directory)
        self.select_time_dir_button.grid(column=0, row=9, columnspan=3, sticky='ew')
        self.set_controls_state(DISABLED)
        
        # Save/Load Settings Buttons
        self.save_button = Button(self.frame9, text="Save Settings", command=self.save_settings)
        self.save_button.pack(pady=(10, 2), fill='x')
        
        self.load_button = Button(self.frame9, text="Load Settings", command=self.load_settings)
        self.load_button.pack(pady=(0, 10), fill='x')

        self.stop_button.config(state=DISABLED)
        self.vsweep_stop.config(state=DISABLED)
        self.timelogstop_button.config(state=DISABLED)
        super().__init__()
    
    def sanitize_filename(self, name):
        """Return a safe filename by replacing invalid characters."""
        return re.sub(r'[^\w\-_. ]', '_', name)
   
    def get_settings_dict(self):
        return {
            "IV_sweep": {
                "start": self.start_box.get(),
                "end": self.end_box.get(),
                "steps": self.step_box.get()
            },
            "loop": {
                "I_min": self.lownode.get(),
                "I_start": self.startnode.get(),
                "I_max": self.highnode.get(),
                "I_step": self.stepsize.get(),
                "loops": self.loopno.get()
            },
            "manual": {
                "compliance": self.Vlimit_box.get(),
                "voltage": self.V_box.get(),
                "step": self.V_step_box.get(),
                "four_wire": self.four_wire_manual.get()
            },
            "run": {
                "voltage_limit": self.vlimit_box.get(),
                "buffer": self.ave_box.get(),
                "mode": self.CheckVar1.get(),
                "four_wire": self.four_wire_var.get()
            },
            "time_log": {
                "voltage": self.volts_set.get(),
                "compliance": self.currentmax_set.get(),
                "interval": self.time_inter_set.get(),
                "duration": self.time_stop_set.get(),
                "filename": self.f_name.get(),
                "four_wire": self.four_wire_time.get(),
                "buffer": self.time_buffer_set.get()
            },
            "voltage_sweep": {
                "start": self.vsweep_start.get(),
                "end": self.vsweep_end.get(),
                "points": self.vsweep_points.get(),
                "buffer": self.vsweep_buffer.get(),
                "compliance": self.vsweep_compliance.get(),
                "sample_name": self.vsweep_sample.get(),
                "save_dir": self.vsweep_save_dir.get(),
                "four_wire": self.vsweep_4w_var.get()
            },
   
            "sensitivity": {
                "voltage_range": self.voltage_range_var.get(),
                "current_range": self.current_range_var.get()
            }

        }


    def apply_settings_dict(self, data):
        try:
            # IV sweep
            self.start_box.delete(0, END)
            self.start_box.insert(0, data["IV_sweep"]["start"])
            self.end_box.delete(0, END)
            self.end_box.insert(0, data["IV_sweep"]["end"])
            self.step_box.delete(0, END)
            self.step_box.insert(0, data["IV_sweep"]["steps"])
    
            # Loop
            self.lownode.delete(0, END)
            self.lownode.insert(0, data["loop"]["I_min"])
            self.startnode.delete(0, END)
            self.startnode.insert(0, data["loop"]["I_start"])
            self.highnode.delete(0, END)
            self.highnode.insert(0, data["loop"]["I_max"])
            self.stepsize.delete(0, END)
            self.stepsize.insert(0, data["loop"]["I_step"])
            self.loopno.delete(0, END)
            self.loopno.insert(0, data["loop"]["loops"])
    
            # Manual
            self.Vlimit_box.delete(0, END)
            self.Vlimit_box.insert(0, data["manual"]["compliance"])
            self.V_box.delete(0, END)
            self.V_box.insert(0, data["manual"]["voltage"])
            self.V_step_box.delete(0, END)
            self.V_step_box.insert(0, data["manual"]["step"])
            self.four_wire_manual.set(data["manual"].get("four_wire", 0))
    
            # Sweep/loop control
            self.vlimit_box.delete(0, END)
            self.vlimit_box.insert(0, data["run"]["voltage_limit"])
            self.ave_box.delete(0, END)
            self.ave_box.insert(0, data["run"]["buffer"])
            self.CheckVar1.set(data["run"]["mode"])
            self.four_wire_var.set(data["run"].get("four_wire", 1))
    
            # Time log
            self.volts_set.delete(0, END)
            self.volts_set.insert(0, data["time_log"]["voltage"])
            self.currentmax_set.delete(0, END)
            self.currentmax_set.insert(0, data["time_log"]["compliance"])
            self.time_inter_set.delete(0, END)
            self.time_inter_set.insert(0, data["time_log"]["interval"])
            self.time_stop_set.delete(0, END)
            self.time_stop_set.insert(0, data["time_log"]["duration"])
            self.f_name.delete(0, END)
            self.f_name.insert(0, data["time_log"]["filename"])
            self.four_wire_time.set(data["time_log"].get("four_wire", 0))
            self.time_buffer_set.delete(0, END)
            self.time_buffer_set.insert(0, data["time_log"].get("buffer", "10"))
            # Voltage sweep
            self.vsweep_start.delete(0, END)
            self.vsweep_start.insert(0, data["voltage_sweep"]["start"])
            self.vsweep_end.delete(0, END)
            self.vsweep_end.insert(0, data["voltage_sweep"]["end"])
            self.vsweep_points.delete(0, END)
            self.vsweep_points.insert(0, data["voltage_sweep"]["points"])
            self.vsweep_buffer.delete(0, END)
            self.vsweep_buffer.insert(0, data["voltage_sweep"]["buffer"])
            self.vsweep_compliance.delete(0, END)
            self.vsweep_compliance.insert(0, data["voltage_sweep"]["compliance"])
            self.vsweep_sample.delete(0, END)
            self.vsweep_sample.insert(0, data["voltage_sweep"]["sample_name"])
            self.vsweep_save_dir.set(data["voltage_sweep"]["save_dir"])
            self.vsweep_4w_var.set(data["voltage_sweep"].get("four_wire", 0))
            
            # Sensitivity settings
            self.voltage_range_var.set(data.get("sensitivity", {}).get("voltage_range", "auto"))
            self.current_range_var.set(data.get("sensitivity", {}).get("current_range", "auto"))

    
            self.dialogue_queue.put("Settings loaded successfully.")
        except Exception as e:
            self.dialogue_queue.put(f"Failed to apply settings: {e}")

    
    
    def vsweep_run_thread(self):
        vsweepthread=Thread(target=self.collect_data, daemon=True)
        vsweepthread.start()
        self.set_controls_state(DISABLED)
        
        self.create_a_plot('voltage')
        
    def save_settings(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(self.get_settings_dict(), f, indent=4)
                self.dialogue_queue.put(f"Settings saved to {file_path}")
            except Exception as e:
                self.dialogue_queue.put(f"Error saving settings: {e}")

    def load_settings(self):
        file_path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                self.apply_settings_dict(data)
            except Exception as e:
                self.dialogue_queue.put(f"Error loading settings: {e}")

    def set_controls_state(self, state):
        """Enable or disable main control buttons depending on connection status."""
        self.go_button.config(state=state)
        self.button.config(state=state)
        self.timelogstart_button.config(state=state)
        self.vsweep_run.config(state=state)
        self.plus_button.config(state=state)
        self.minus_button.config(state=state)
    
    def make_connection(self):
        self.connectionthread=Thread(target=self.connect,daemon=True)
        
        self.connectionthread.start()
    
    def connect(self):
        
        if self.connection==None:
            self.connectbutton.config(state=DISABLED)
            self.connection=ConnectKeithley(self.dialogue_queue,probe_timeout=5000)
            self.query, self.sourcemeter, self.resource=self.connection.find()
            if self.query:
                self.dialogue_queue.put("Keithley connection successful.")
                self.connection_status.config(text="Connected", fg="green")
                self.set_controls_state(NORMAL)
                self.stop_button.config(state=NORMAL)
                self.vsweep_stop.config(state=NORMAL)
                self.timelogstop_button.config(state=NORMAL)
                self.sweep_stop_button.config(state=NORMAL)
            else:
                self.dialogue_queue.put("Keithley connection failed.")
                self.connection_status.config(text="Not Connected", fg="red")
                self.set_controls_state(DISABLED)
                self.stop_button.config(state=DISABLED)
                self.vsweep_stop.config(state=DISABLED)
                self.timelogstop_button.config(state=DISABLED)
                self.connection=None
            self.connectbutton.config(state=NORMAL)
        
            
    def disconnect(self):
        if self.sourcemeter:
            try:
                self.dialogue_queue.put("Disconnecting Keithley...")
                self.sourcemeter.shutdown()
                if hasattr(self.sourcemeter, 'adapter') and self.sourcemeter.adapter:
                    self.sourcemeter.adapter.connection.close()
                self.dialogue_queue.put("Keithley disconnected.")
                self.connection_status.config(text="Not Connected", fg="red")
            except Exception as e:
                self.dialogue_queue.put(f"Error during disconnect: {e}")
            finally:
                self.sourcemeter = None
                self.connection=None
                self.query = False
                self.set_controls_state(DISABLED)
        else:
            self.dialogue_queue.put("No Keithley connected.")
            self.connection=None

   
    
    def select_save_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.save_dir.set(directory)
            self.dialogue_queue.put(f"Save directory set to: {directory}")
    def select_time_log_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.time_log_dir.set(directory)
            self.dialogue_queue.put(f"Time log directory set to: {directory}")
    def _update_dialogue_box(self, text):
        try:
            self.dialogbox.config(state=NORMAL)
            self.dialogbox.insert(END, text + '\n')
            self.dialogbox.yview(END)
            self.dialogbox.config(state=DISABLED)
        except TclError:
            pass
            
    def dialogue_queue_worker(self):
        while True:
            text = self.dialogue_queue.get()
            if text is None:
                break
            # Schedule GUI update on main thread
            self._update_dialogue_box(text)
            
            
    def log_time_thread(self):
        
       
        if not self.running:
            self.running=True
            self.t3=Thread(target=self.log_I, args=(self.time_data_queue,self.resource),daemon=True)
            self.t3.start()
            self.set_controls_state(DISABLED)
            
            self.create_a_time_plot()
   
    def threading1(self):
        
        t1=Thread(target=self.apply, daemon=True)
        t1.start()
    def threading2(self):
        
        self.running=True
        self.t2=Thread(target=self.collect_data1, args=(self.data_queue,),daemon=True)
        self.t2.start()
        self.set_controls_state(DISABLED)
        self.create_a_plot('current')
    
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
                
                ax.errorbar(data[0], data[1], yerr=data[2], color='black', marker='o')
                ax.set_xlabel('Time /s')
                ax.set_ylabel('Current /A')
                  
                self.canvas.draw()
                
                
            if self.running:
               
                self.plot_win_time.after(100, update_time_plot)  # Check for new data every 100ms
    
        # Start the update loop
        update_time_plot()
        
    def create_a_plot(self, source='current'):
        """Collect data from the sourcemeter and plot it."""
        self.source_type=source
        # Create window for real-time spectrum plot
        self.plot_win = Toplevel(self.master)
        self.plot_win.geometry("500x500")
        self.plot_win.title('I-V curve')
        self.plot_win.resizable(True, True)
    
        # Set up the figure and canvas
        fig, ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_win)
        self.canvas.get_tk_widget().pack()
        toolbar = NavigationToolbar2Tk(self.canvas, self.plot_win)
        toolbar.update()
        
        if self.source_type=='current':
            ax.set_xlabel('Current /A')
            ax.set_ylabel('Voltage /V')
        else:
            ax.set_ylabel('Current /A')
            ax.set_xlabel('Voltage /V')
            
            
        def update_plot():
            if not self.data_queue.empty():
                data = self.data_queue.get()
                ax.clear()
                if self.source_type == 'current':
                    ax.errorbar(data[0], data[1], yerr=data[2], color='black', marker='o')
                    ax.set_xlabel('Current /A')
                    ax.set_ylabel('Voltage /V')  
                else:
                    ax.errorbar(data[0], data[1], yerr=data[2], color='black', marker='o')
                    ax.set_xlabel('Voltage /V')
                    ax.set_ylabel('Current /A')  

                
                self.canvas.draw()
                
                
            if self.running:
               
                self.plot_win.after(100, update_plot)  # Check for new data every 100ms
    
        # Start the update loop
        update_plot()
    def safe_shutdown(self):
        try:
            self.sourcemeter.shutdown()
        except KeyError as e:
            self.dialogue_queue.put(f"Warning: Shutdown failed due to unexpected response: {e}")
            try:
                self.sourcemeter.write("OUTP OFF")
            except Exception:
                pass
   

class ConnectKeithley:
    
    def __init__(self, dialogue_queue,probe_timeout=5000):
        self.rm = visa.ResourceManager()
        self.dialogue_queue = dialogue_queue
        self.probe_timeout = probe_timeout
    def find(self):
        self.finding=True
        self.devicelist = self.rm.list_resources()
        d_list = list(self.devicelist)
        d_list.reverse()  # optional: prioritize newer devices first
        self.dialogue_queue.put(f'The device list is {self.devicelist}')

        for resource in d_list:
            try:
                self.dialogue_queue.put(f'Trying to connect to {resource}...')
                
                # Handle serial resources explicitly
                if "ASRL" in resource or "COM" in resource:
                    adapter = VISAAdapter(
                        resource,
                        timeout=self.probe_timeout,
                        baud_rate=9600,
                        data_bits=8,
                        stop_bits=StopBits.one,
                        parity=Parity.none,
                        flow_control=0,
                        write_termination="\r",
                        read_termination="\r"
                    )
                else:
                    adapter = VISAAdapter(resource, timeout=self.probe_timeout)

                self.sm = Keithley2400(adapter)
                idn = self.sm.id.strip()
                self.dialogue_queue.put(f'Response: {idn}')

                if "KEITHLEY" in idn and "2400" in idn:
                    self.dialogue_queue.put(f'Connected to Keithley 2400 at {resource}')
                    self.finding=False
                    return True, self.sm, resource

            except Exception as e:
                self.dialogue_queue.put(f'Failed to connect to {resource}: {e}')
                self.finding=False
                continue

        self.dialogue_queue.put("Keithley 2400 not found.")
        self.dialogue_queue.put("Check the Keithley is in RS232 mode, baud =9600, bits =8, parity= none, flow control= none, read termination= CR")
        self.dialogue_queue.put("and or try switch on and off and replug the USB in.")
        self.finding=False
        return False, None, None
        
    def set_timeout(self, ms: int):
        """Adjust the VISA timeout (in milliseconds) on the current device."""
        # assume you stored the adapter or the sm object as self.sm
        self.sm.adapter.timeout = ms
        # if needed:
        # self.sm.adapter.session.timeout = ms        
            
if __name__=='__main__':   
    
    try:
        del enumerate  # if it's been overridden
    except:
        pass
    
    def on_closing():
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            try:
                if app.sourcemeter is not None:
                    app.disconnect()
                    app.dialogue_queue.put("Keithley shut down.")
                    app.dialogue_queue.put(None)
            except Exception as e:
                print(f"Error during shutdown: {e}")
            finally:
                root.destroy()
    
    warnings.filterwarnings("ignore", category=UserWarning, module='pyvisa_py.tcpip')
    sourcemeter=None         
    root=Tk()
    
    app=App(root, sourcemeter)
    root.protocol("WM_DELETE_WINDOW", on_closing)
    mainloop()
    
    

        
        
