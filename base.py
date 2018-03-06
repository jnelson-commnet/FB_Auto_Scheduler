__author__ = 'Jack'

import os
import sys
import pandas as pd
import numpy as np

from prog import scheduler as sch

# save current working directory as homey
homey = os.path.abspath(os.path.dirname(__file__))
# homey = os.getcwd() # works in jupyter notebook

# set directory paths
dataPath = os.path.join(homey, 'data')
progPath = os.path.join(homey, 'prog')
simPath = os.path.join(homey, 'FB_Sim')
forcPath = os.path.join(simPath, 'ForecastRedoux')
# this should probably be moved out of the simulator and into the main sql area, where that ends up
sqlPath = os.path.join(forcPath, 'SQL')

# set paths to excel files
forecastFilename = os.path.join(dataPath, 'RegularForecast.xlsx')
mfgCentersFilename = os.path.join(dataPath, 'MfgCenters.xlsx')
moFilename = os.path.join(dataPath, 'MOs.xlsx')
laborAvailFilename = os.path.join(dataPath, 'LaborAvailablePerDay.xlsx')
leadFilename = os.path.join(dataPath, 'LeadTimes.xlsx')

# going to borrow some of the FB_Sim to run queries
### HEY! This would be good to move for better access and clarity
sys.path.insert(0, forcPath)
import ForecastMain as fm
import ForecastAPI as fa
# pull the usual FB_Sim queries
fa.run_queries(queryPath=sqlPath, dataPath=dataPath)

### -----------------------------------
# This section uses the MO's listed in Fishbowl as well as the Mfg Centers to create an
#	estimate of labor needed and a priority of work to be done.

# save mfgCenters as dataFrame, includes MFG Center assignments and Setup/labor time estimates
mfgCenters = pd.read_excel(mfgCentersFilename, header=0)

# save current Manufacture Orders
modf = pd.read_excel(moFilename, header=0)

# make a date list with labor availability
dateList = sch.create_date_list(dailyLabor=11)

# run the auto schedule to get an ideal schedule by priority
moLinesLabor = sch.run_auto_schedule(modf=modf, mfgCenters=mfgCenters, dateList=dateList)

# use the last scheduled FG in an order to save an ideal schedule
idealSchedule = moLinesLabor.drop_duplicates('ORDER', keep='last')

# replace the schedule dates on the MO order lines with the new dates for those orders
newMOdf = pd.merge(modf.copy(), idealSchedule[['ORDER', 'NewDate']].copy(), how='left', on='ORDER')
newMOdf['DATESCHEDULED'] = newMOdf['NewDate'].copy()
newMOdf.drop(labels='NewDate', axis=1, inplace=True)




