import sys #Module to access the computer
import os

homey = os.path.abspath(os.path.dirname(__file__))
redouxPath = os.path.join(homey, 'ForecastRedoux')
# print(redouxPath)
# print('ok')

sys.path.insert(0, redouxPath) #Pull up the file with the forecast information

import ForecastMain #Import the actual forecast python file

print('----------------------')
print('SQL Queries? (y or n)')
print('')
sqlInput = input()

if sqlInput == 'y':
	sqlState = True
else:
	sqlState = False

print('----------------------')
print('Add Imaginary builds? (y or n)')
print('')
imagInput = input()

if imagInput == 'y':
	imagState = True
else:
	imagState = False

print('----------------------')
print('Remove problematic Sales Orders? (y or n)')
print('')
orderInput = input()

if orderInput == 'y':
	orderState = True
else:
	orderState = False

print('----------------------')
print('Ignore schedule? (y or n)')
print('')
schedInput = input()

if schedInput == 'y':
	schedState = True
else:
	schedState = False

ForecastMain.run_normal_forecast_tiers_v2(
	ignore_schedule_errors=schedState, 
	add_stock_builds=imagState, 
	ignore_orders=orderState, 
	sql_queries=sqlState
) #Run the actual forecast