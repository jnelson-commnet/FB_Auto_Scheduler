

import sys
import os

homey = os.path.abspath(os.path.dirname(__file__))
redouxPath = os.path.join(homey, 'ForecastRedoux')

sys.path.insert(0, redouxPath) #Pull up the file with the forecast information

import ForecastMain #Import the actual forecast python file

ForecastMain.run_normal_forecast_tiers_v2(ignore_schedule_errors=True, add_stock_builds=True, ignore_orders=True, sql_queries=False) #Run the actual forecast