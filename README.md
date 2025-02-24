# Keithley2400_Control
A simple GUI using tinkter to control a Keithley 2400 source meter via a RS232 adapter.  It will find the correct adapter based on the Keithley id return.
Data collected is saved as a .csv using the time-date as part of the filename and it will be saved in the same path as the code.  
Manual control allows stepping up and down of voltage but long term use may result in SM errors (untested).
Stop will abort sweeps, loops, or manual control voltage.
Data is ploted live using a seperate window.

Please acknowledge Kevin Critchley if data collected using the code is disseminated.
