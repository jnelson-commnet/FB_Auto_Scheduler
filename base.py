__author__ = 'Jack'

### IMPORTS ###

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
queryPath = os.path.join(dataPath, 'query')

# set paths to excel files
forecastFilename = os.path.join(dataPath, 'RegularForecast.xlsx')
mfgCentersFilename = os.path.join(dataPath, 'MfgCenters.xlsx')
moFilename = os.path.join(dataPath, 'MOs.xlsx')
laborAvailFilename = os.path.join(dataPath, 'LaborAvailablePerDay.xlsx')
leadFilename = os.path.join(dataPath, 'LeadTimes.xlsx')
finalSchedFilename = os.path.join(homey, 'finalSchedule.xlsx')

### QUERIES ###

# going to borrow some of the FB_Sim to run queries
### HEY! This would be good to move for better access and clarity
sys.path.insert(0, forcPath)
import ForecastMain as fm
import ForecastAPI as fa
# pull the usual FB_Sim queries
# fa.run_queries(queryPath=sqlPath, dataPath=dataPath)

# Live server:
sys.path.insert(0, 'Z:\Python projects\FishbowlAPITestProject')
import connecttest
# myresults = connecttest.create_connection(queryPath, 'leadtimequery.txt')
# myexcel = connecttest.makeexcelsheet(myresults)
# connecttest.save_workbook(myexcel, dataPath, 'LeadTimes.xlsx')
# myresults = connecttest.create_connection(queryPath, 'mfgcenterquery.txt')
# myexcel = connecttest.makeexcelsheet(myresults)
# connecttest.save_workbook(myexcel, dataPath, 'MfgCenters.xlsx')


### GET DATA ###

# save mfgCenters as df, includes MFG Center assignments and Setup/labor time estimates
mfgCenters = pd.read_excel(mfgCentersFilename, header=0)
# save current Manufacture Orders
modf = pd.read_excel(moFilename, header=0)
# save lead time estimates
leadTimes = pd.read_excel(leadFilename, header=0)
# the lead time estimates are drawing from a couple fields
# the following section sorts out the preferred lead time for each part and adds it to the "LeadTimes" column
leadTimes.sort_values(['PART','DefaultVendor','LastDate'], ascending=[True,False,False], inplace=True)
leadTimes.drop_duplicates('PART', keep='first', inplace=True)
leadTimes['LeadTimes'] = np.nan
x=0
while x < len(leadTimes):
    if leadTimes['RealLeadTime'].iat[x] > 0:
        leadTimes['LeadTimes'].iat[x] = leadTimes['RealLeadTime'].iat[x]
    elif leadTimes['VendorLeadTime'].iat[x] > 0:
        leadTimes['LeadTimes'].iat[x] = leadTimes['VendorLeadTime'].iat[x]
    x+=1
leadTimes = leadTimes[['PART','Make/Buy','AvgCost','LeadTimes']].copy()
### this is a bandaid, I think there will be problems with NAN values later.  Need to figure out eventually.
leadTimes.fillna(10, inplace=True)

# this is a placeholder for a calculation of start to finish time for a build.
# just using it for earliest schedule date right now.
orderRunTime = 7

### MAKE DATE LIST ###

# creating a common timestamp, if not added they can all generate their own seconds off from each other
todayTimestamp = pd.Timestamp.today()
# make a date list with labor availability
dateList = sch.create_date_list(todayTimestamp=todayTimestamp, dailyLabor=11)
## labor type testing
dateListProLine = sch.create_date_list(todayTimestamp=todayTimestamp, dailyLabor=40)
dateListRacking = sch.create_date_list(todayTimestamp=todayTimestamp, dailyLabor=12)
dateListPCB = sch.create_date_list(todayTimestamp=todayTimestamp, dailyLabor=24)
dateListLabels = sch.create_date_list(todayTimestamp=todayTimestamp, dailyLabor=7)
dateListKitting = sch.create_date_list(todayTimestamp=todayTimestamp, dailyLabor=12)
dateListShipping = sch.create_date_list(todayTimestamp=todayTimestamp, dailyLabor=6)
dateListCableAssy = sch.create_date_list(todayTimestamp=todayTimestamp, dailyLabor=6)

### CREATE IDEAL SCHEDULE ###

# prep mo list with mfg centers and labor estimates
preppedMOdf = sch.pre_schedule_prep(modf=modf.copy(), mfgCenters=mfgCenters.copy())
# add an empty datetime column
#   - this allows the use of the same scheduling formula throughout the script
#### not sure if this is actually being used yet.  Probably need to change from sch.run_auto_schedule to sch.sched_with_date_limits.
preppedMOdf['EarliestScheduleDate'] = np.nan
preppedMOdf['EarliestScheduleDate'] = pd.to_datetime(preppedMOdf['EarliestScheduleDate'])
# run the auto schedule to get an ideal schedule by priority
moLinesLabor = sch.run_auto_schedule(moLinesLabor=preppedMOdf.copy(), dateList=dateList.copy())
## labor type testing
moLinesLaborProLine = sch.run_auto_schedule(moLinesLabor=preppedMOdf[preppedMOdf['Mfg Center'] == 'Pro Line'].copy(), dateList=dateListProLine.copy())
moLinesLaborRacking = sch.run_auto_schedule(moLinesLabor=preppedMOdf[preppedMOdf['Mfg Center'] == 'Racking'].copy(), dateList=dateListRacking.copy())
moLinesLaborPCB = sch.run_auto_schedule(moLinesLabor=preppedMOdf[preppedMOdf['Mfg Center'] == 'PCB'].copy(), dateList=dateListPCB.copy())
moLinesLaborLabels = sch.run_auto_schedule(moLinesLabor=preppedMOdf[preppedMOdf['Mfg Center'] == 'Labels'].copy(), dateList=dateListLabels.copy())
moLinesLaborKitting = sch.run_auto_schedule(moLinesLabor=preppedMOdf[preppedMOdf['Mfg Center'] == 'Kitting'].copy(), dateList=dateListKitting.copy())
moLinesLaborShipping = sch.run_auto_schedule(moLinesLabor=preppedMOdf[preppedMOdf['Mfg Center'] == 'Shipping'].copy(), dateList=dateListShipping.copy())
moLinesLaborCableAssy = sch.run_auto_schedule(moLinesLabor=preppedMOdf[preppedMOdf['Mfg Center'] == 'Cable Assembly'].copy(), dateList=dateListCableAssy.copy())
## labor type testing
moLinesLaborProLine.drop_duplicates('ORDER', keep='last', inplace=True)
moLinesLaborRacking.drop_duplicates('ORDER', keep='last', inplace=True)
moLinesLaborPCB.drop_duplicates('ORDER', keep='last', inplace=True)
moLinesLaborLabels.drop_duplicates('ORDER', keep='last', inplace=True)
moLinesLaborKitting.drop_duplicates('ORDER', keep='last', inplace=True)
moLinesLaborShipping.drop_duplicates('ORDER', keep='last', inplace=True)
moLinesLaborCableAssy.drop_duplicates('ORDER', keep='last', inplace=True)
## labor type testing
idealSchedule = pd.concat([moLinesLaborProLine.copy(),
		   				   moLinesLaborRacking.copy(),
		   				   moLinesLaborPCB.copy(),
		   				   moLinesLaborLabels.copy(),
		   				   moLinesLaborKitting.copy(),
		   				   moLinesLaborShipping.copy(),
		   				   moLinesLaborCableAssy.copy()])
# use the last scheduled FG in an order to save an ideal schedule
idealSchedule = moLinesLabor.drop_duplicates('ORDER', keep='last')

### RUN THE SIM ###

# replace the schedule dates on the MO order lines with the new dates for those orders
newMOdf = pd.merge(modf.copy(), idealSchedule[['ORDER', 'NewDate']].copy(), how='left', on='ORDER')
newMOdf['DATESCHEDULED'] = newMOdf['NewDate'].copy()
newMOdf.drop(labels='NewDate', axis=1, inplace=True)
# run the new MO schedule through the FB_Sim to find phantom orders
orderTimeline = fm.run_normal_forecast_tiers_v3(dataPath=dataPath, includeSO=False, subMO=newMOdf.copy())

### GET SCHEDULE LIMITS ###

orderLeads = sch.get_earliest_leads(orderTimeline=orderTimeline.copy(),
                                    leadTimes=leadTimes.copy(),
                                    dateList=dateList.copy(),
                                    orderRunTime=orderRunTime)

### ANALYZE AND ADJUST SCHEDULE ###

# sch.analyze_schedule(newMOdf=newMOdf.copy(),
# 					 orderLeads=orderLeads.copy(),
# 					 modf=modf.copy(),
# 					 mfgCenters=mfgCenters.copy(),
# 					 dateList=dateList.copy(),
# 					 orderRunTime=orderRunTime,
# 					 leadTimes=leadTimes.copy())

##labor type testing
finalSchedule = sch.analyze_schedule_labor_types(newMOdf=newMOdf.copy(),
												 orderLeads=orderLeads.copy(),
												 modf=modf.copy(),
												 mfgCenters=mfgCenters.copy(),
												 dateList=dateList.copy(),
												 orderRunTime=orderRunTime,
												 leadTimes=leadTimes.copy(),
												 dateListProLine=dateListProLine.copy(),
												 dateListRacking=dateListRacking.copy(),
												 dateListPCB=dateListPCB.copy(),
												 dateListLabels=dateListLabels.copy(),
												 dateListKitting=dateListKitting.copy(),
												 dateListShipping=dateListShipping.copy(),
												 dateListCableAssy=dateListCableAssy.copy())

# save a copy of the schedule to excel
writer = pd.ExcelWriter(finalSchedFilename)
finalSchedule.to_excel(writer, 'timeline')
writer.save()

print('end of the lines')