# Keithley2400_Control


A simple GUI using tinkter to control a Keithley 2400 source meter via a RS232 adapter.  It will find the correct adapter based on the Keithley 'return'.

I recommend reading the 'user_instructions.ipynb' file

Data collected is saved as a .csv using the time-date as part of the filename and it will be saved in the same path as the code. Use Browse to select your save path. 

Stop will abort sweeps, loops, logs, or manual control voltage.
Data is ploted live using a seperate window.

Current can be data logged, with a constant current applied, with a minimium time interval of about 1 second.

Can also perform voltage sweeps and measure the current.

Settings can be saved to a json and loaded.

Connecting to the Keithley is performed in the app.  It is a little slow because it checks every port.

Please acknowledge Kevin Critchley if data collected using the code is disseminated.
