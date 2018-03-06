__author__ = 'Chris'

import sys #Module to access the computer
import os


### These are various options for getting the current directory
# homey = os.getcwd() # This one doesn't work on the Pi because it's executing elsewhere.
homey = os.path.abspath(os.path.dirname(__file__))
# homey = os.path.realpath('')

# print('top file ----')
# print(homey)

redouxPath = os.path.join(homey, 'ForecastRedoux')
# print(redouxPath)
# print('ok')

sys.path.insert(0, redouxPath) #Pull up the file with the forecast information

import ForecastMain #Import the actual forecast python file

ForecastMain.run_normal_forecast_tiers_v2() #Run the actual forecast

""" The following is only for the version on the Pi """
# import ForecastEmail

# ForecastEmail.send_email()