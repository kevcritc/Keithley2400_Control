# Keithley2400_Control
A simple GUI using tinkter to control a Keithley 2400 source meter via a RS232 adapter (other adapters can be configured).  Line 23 will need to be altered to accomodate your own adaptor.
Data collected is saved as a .csv using the time-date as part of the filename and it will be saved in the same path as the code.  
Manual control allows stepping up and down of voltage but long term use may result in SM errors (untested).
Stop will abort sweeps, loops, or manual control voltage.
