__author__ = 'Jack'

import os
import pandas as pd
import numpy as np

import sys
homey = os.getcwd() # works in jupyter notebook
dataPath = os.path.join(homey, 'data')
progPath = os.path.join(homey, 'prog')
simPath = os.path.join(homey, 'FB_Sim')
forcPath = os.path.join(simPath, 'ForecastRedoux')
sys.path.insert(0, forcPath)
import ForecastMain as fm
import ForecastAPI as fa

def test_sched(x):
	print(x)

# this is in use, but seems pretty unnecessary.  Will probably delete later.
def labor_total(orderLabor, usedLabor, extraLabor):
    totalLabor = orderLabor + usedLabor + extraLabor
    return totalLabor


# trying to wrap all the scheduling parts into functions

# This function creates a table of dates with labor availability.
#### HEY! dailyLabor is an arbitrary labor estimate hard coded!
#### This should be replaced by either an input that can be adjusted or maybe even a sheet that accounts for PTO and stuff.
def create_date_list(dailyLabor=10):
	# create a list of dates starting with today.
	dateList = pd.DataFrame({'StartDate': pd.date_range(pd.Timestamp.today(), periods=2000, freq='1D'), 'DaysFromStart': np.nan, 'AvailableLabor': np.nan})

	# add a column with integers representing the day of the week. (0 is monday, 1 is tuesday ....)
	dateList['weekday'] = pd.DatetimeIndex(dateList['StartDate']).dayofweek

	# remove saturday and sunday
	dateList = dateList[dateList['weekday'] != 5]
	dateList = dateList[dateList['weekday'] != 6]

	# fill out the dayFromStart column with integers increasing by 1.  This will be used to calculate labor availability later.
	x = 1
	for index in dateList.index:
	    dateList.at[index, 'DaysFromStart'] = x
	    x+=1

	#### HEY! This is an arbitrary labor estimate hard coded!
	#### This should be replaced by either an input that can be adjusted or maybe even a sheet that accounts for PTO and stuff.
	dateList['DailyLabor'] = dailyLabor

	# calculate total labor available as of each date.  This is making the 'DaysFromStart' column pretty unnecessary but I'm keeping it for now.
	x = 0
	for index in dateList.index:
	    dateList.at[index, 'AvailableLabor'] = dateList.at[index, 'DailyLabor'].copy() + x
	    x = dateList.at[index, 'AvailableLabor'].copy()

	# return the resulting dataFrame
	return(dateList.copy())

# prepares order list for a schedule run by adding mfg centers and labor estimates
def pre_schedule_prep(modf, mfgCenters):
	# getting a list of Finished Goods on MO's
	moFgOnly = modf[modf['ORDERTYPE'] == 'Finished Good'].copy()

	# sorting by date so the earliest scheduled can be the highest priority
	moFgOnly.sort_values('DATESCHEDULED', inplace=True)

	# renaming part column to match MO header
	mfgCenters.rename(columns={'Part':'PART'}, inplace=True)

	# adding centers and labor estimates to MO lines
	moLinesLabor = pd.merge(moFgOnly.copy(), mfgCenters.copy(), how='left', on='PART')

	# save missing info for later.  Will want user to see what items were missed for lack of data.
	missingCenters = moLinesLabor[moLinesLabor['Mfg Center'].isnull()].copy()
	missingSetup = moLinesLabor[moLinesLabor['Setup'].isnull()].copy()
	missingLabor = moLinesLabor[moLinesLabor['LaborPer'].isnull()].copy()

	# just filling N/A in a way that doesn't throw errors, will need these to be 0 for easy maths
	moLinesLabor['SetupTemp'] = moLinesLabor['Setup'].fillna(0)
	moLinesLabor['LaborPerTemp'] = moLinesLabor['LaborPer'].fillna(0)
	moLinesLabor.drop(['Setup','LaborPer'], axis=1, inplace=True)
	moLinesLabor.rename(columns={'SetupTemp':'Setup','LaborPerTemp':'LaborPer'}, inplace=True)

	# create a column for the total labor required for each order
	moLinesLabor['LaborRequired'] = moLinesLabor['Setup'] + (moLinesLabor['LaborPer'] * moLinesLabor['QTYREMAINING'])
	return(moLinesLabor.copy())
	

# create a new schedule based on the current MO dates and available labor by date
def run_auto_schedule(moLinesLabor, dateList):
	# calculate cumulative labor needed for builds in their current date order
	moLinesLabor['CumulativeLaborRequired'] = np.nan
	x = 0
	for index in moLinesLabor.index:
	    moLinesLabor.at[index, 'CumulativeLaborRequired'] = moLinesLabor.at[index, 'LaborRequired'].copy() + x
	    x = moLinesLabor.at[index, 'CumulativeLaborRequired'].copy()


	### -----------------------------------
	# This section compares labor availability to labor needed to create a schedule.

	# add new column with estimated schedule date.  For each row, compare the cumulative labor to the dateList.
	# if the cumulative labor is less than the total labor available, then set the date.
	moLinesLabor['NewDate'] = np.nan
	for index in moLinesLabor.index:
	    laborNeeded = moLinesLabor.at[index, 'CumulativeLaborRequired'].copy()
	    tempDateList = dateList[dateList['AvailableLabor'] >= laborNeeded].copy()
	    newDate = tempDateList['StartDate'].iat[0]
	    moLinesLabor.at[index, 'NewDate'] = newDate

	return(moLinesLabor.copy())

# create a new schedule based on the current MO dates and available labor by date
# also consider earliest allowed schedule dates
def sched_with_date_limits(orderPriority, dateList):
	# looping through order lines to auto schedule
	# if it comes up with a schedule date before the earliest allowed,
	# it will move onto the next line to search for another order that can fit
	# create output schedule dataFrame and a variable to hold total unused labor
	outputSchedule = pd.DataFrame(columns=['ORDER','LaborRequired','EarliestScheduleDate','NewDate'])
	unusedLabor = 0
	lH = 0
	while lH < len(orderPriority):
	    # collect labor needed and get relevant schedule date
	    totalLabor = labor_total(orderLabor=orderPriority['LaborRequired'].iat[lH],
	                             usedLabor=outputSchedule['LaborRequired'].sum(),
	                             extraLabor=unusedLabor)
	    tempDate = dateList[dateList['AvailableLabor'] >= totalLabor].head(1)
	    schedDate = tempDate['StartDate'].iat[0]
	    if schedDate < orderPriority['EarliestScheduleDate'].iat[lH]:
	        # if the schedule date is before the line can schedule then move on
	        lH+=1
	        if lH >= len(orderPriority):
	            # if there are no more priorities then there can only be orders held by their earliest schedule dates
	            # temporarily sort by earliest allowed date to find the next order to schedule
	            orderPriority.sort_values('EarliestScheduleDate', inplace=True)
	            lH = 0
	            schedDate = orderPriority['EarliestScheduleDate'].iat[0]
	            outputSchedule = outputSchedule.append({'ORDER':orderPriority['ORDER'].iat[lH],
	                                                    'LaborRequired':orderPriority['LaborRequired'].iat[lH],
	                                                    'EarliestScheduleDate':orderPriority['EarliestScheduleDate'].iat[lH],
	                                                    'NewDate':schedDate},
	                                                    ignore_index=True)
	            orderPriority.drop(orderPriority.index[lH], inplace=True)
	            orderPriority.sort_values('DATESCHEDULED', inplace=True)
	            # now that it's set, we need to add value to unused labor (any labor skipped due to material timing)
	            # otherwise overlapping earliest schedule dates could overlap and double up on available labor
	            tempDate = dateList[dateList['StartDate'] == schedDate]
	            availLabor = tempDate['AvailableLabor'].iat[0]
	            usedLabor = outputSchedule['LaborRequired'].sum() + unusedLabor
	            laborGap = availLabor - usedLabor
	            unusedLabor = laborGap + unusedLabor
	    else:
	        # otherwise add a schedule line to the output and delete the order from the labor list
	        outputSchedule = outputSchedule.append({'ORDER':orderPriority['ORDER'].iat[lH],
	                                                'LaborRequired':orderPriority['LaborRequired'].iat[lH],
	                                                'EarliestScheduleDate':orderPriority['EarliestScheduleDate'].iat[lH],
	                                                'NewDate':schedDate},
	                                                ignore_index=True)
	        orderPriority.drop(orderPriority.index[lH], inplace=True)
	        # set the iterator back to 0 to start back at the top of the remaining priority list
	        lH = 0
	# the output schedule should be finished
	return(outputSchedule.copy())

# method of retrieving earliest allowed schedule dates from phantom orders after simulator run
# orderRunTime is defaulting to 7 days but could be made more exact per order.
#	it would require dividing required labor by the average available labor per day.
def get_earliest_leads(orderTimeline, leadTimes, dateList, orderRunTime=7):
	# get a list of phantom orders and their grandparent orders
	### Currently phantom orders are placed a day before the order with the shortage will finish.  So
	###     if the lead time field is used later, this could throw the phantom schedule dates.  I'll
	###     try to avoid this by getting back to the shortage date, but it might become redundant later.
	phantoms = orderTimeline[orderTimeline['ITEM'] == 'Phantom'].copy()
	buyPhantoms = phantoms[phantoms['Make/Buy'] == 'Buy'].copy()
	# add the lead times to each part
	leadPhantoms = pd.merge(buyPhantoms.copy(), leadTimes[['PART','LeadTimes']].copy(), how='left', on='PART')
	# lose unnecessary columns
	freshLeads = leadPhantoms[['GRANDPARENT','LeadTimes']].copy()
	# sort by grandparent and then lead time to make sure the highest lead time comes first
	freshLeads.sort_values(by=['GRANDPARENT','LeadTimes'], ascending=[True, False], inplace=True)
	# drop duplicate grandparents leaving the longest lead as the only one remaining
	freshLeads.drop_duplicates('GRANDPARENT', keep='first', inplace=True)
	# rename column for easy merge
	freshLeads.rename(columns={'GRANDPARENT':'ORDER'}, inplace=True)
	# adjust the lead time to account for time to place/receive order (2 days) and expected run time for the build
	# replace orderRunTime with a calculation of labor needed against average labor available per day
	freshLeads['AdjustedLeadTimes'] = freshLeads['LeadTimes'] + 2 + orderRunTime
	# Add comparative dates from dateList
	freshLeads = pd.merge(freshLeads.copy(),
						  dateList[['DaysFromStart','StartDate']].copy(),
						  how='left', left_on='AdjustedLeadTimes', right_on='DaysFromStart')
	# rename the start date column to earliest schedule date
	freshLeads.rename(columns={'StartDate':'EarliestScheduleDate'}, inplace=True)
	return(freshLeads.copy())

# quick method of combining the order lead lists and keeping only the highest date
def combine_order_leads(oldLeads, newLeads):
	# append the new list of earliest schedule dates to the old
	combinedLeads = oldLeads.copy().append(newLeads.copy())
	# sort by order and then by latest schedule date first
	combinedLeads.sort_values(by=['ORDER','EarliestScheduleDate'], ascending=[True, False], inplace=True)
	# drop duplicate orders and keep first so it highest date
	combinedLeads.drop_duplicates('ORDER', keep='first', inplace=True)
	return(combinedLeads.copy())

#
def analyze_schedule(newMOdf, orderLeads, modf, mfgCenters, dateList, orderRunTime, leadTimes):
	print('in analyze_schedule')
	tempMOdf = newMOdf.sort_values(by=['ORDER','DATESCHEDULED'], ascending=[True, True]).copy()
	tempMOdf.drop_duplicates('ORDER', keep='first', inplace=True)
	checkSched = pd.merge(tempMOdf[['ORDER','DATESCHEDULED']].copy(),
						  orderLeads[['ORDER','EarliestScheduleDate']].copy(),
						  how='left', on='ORDER')
	checkSched['TimeDiff'] = np.nan
	for each in range(0, len(checkSched)):
	    if checkSched['DATESCHEDULED'].iat[each] < checkSched['EarliestScheduleDate'].iat[each]:
	        checkSched['TimeDiff'] = 'here'
	        print(checkSched['ORDER'].iat[each])
	if len(checkSched.dropna()) != 0:
		schedule_loop(modf=modf.copy(),
					  orderLeads=orderLeads.copy(),
					  mfgCenters=mfgCenters.copy(),
					  dateList=dateList.copy(),
					  orderRunTime=orderRunTime,
					  leadTimes=leadTimes.copy())
	else:
		print('no schedule issues found')
		return(newMOdf.copy())

#
def schedule_loop(modf, orderLeads, mfgCenters, dateList, orderRunTime, leadTimes):
	print('in schedule_loop')
	### CREATE NEW SCHEDULE ###

	# save a new copy of the modf with longest leads added
	leadMOdf = pd.merge(modf.copy(), orderLeads[['ORDER','EarliestScheduleDate']].copy(), how='left', on='ORDER')
	moLinesLabor = pre_schedule_prep(modf=leadMOdf, mfgCenters=mfgCenters.copy())
	outputSchedule = sched_with_date_limits(orderPriority=moLinesLabor.copy(),
	                                            dateList=dateList.copy())
	# use the last scheduled FG in an order to save a new schedule
	newSchedule = outputSchedule.drop_duplicates('ORDER', keep='last').copy()

	### RUN THE SIM ###

	# replace the schedule dates on the MO order lines with the new dates for those orders
	newMOdf = pd.merge(modf.copy(), newSchedule[['ORDER', 'NewDate']].copy(), how='left', on='ORDER')
	newMOdf['DATESCHEDULED'] = newMOdf['NewDate'].copy()
	newMOdf.drop(labels='NewDate', axis=1, inplace=True)
	# run the new MO schedule through the FB_Sim to find phantom orders
	orderTimeline = fm.run_normal_forecast_tiers_v3(dataPath=dataPath, includeSO=False, subMO=newMOdf.copy())

	### GET SCHEDULE LIMITS ###

	# get a fresh list of earliest leads per order from the recent sim run
	freshLeads = get_earliest_leads(orderTimeline=orderTimeline.copy(),
	                                    leadTimes=leadTimes.copy(),
	                                    dateList=dateList.copy(),
	                                    orderRunTime=orderRunTime)
	# combine it with any previous lists to get the last schedule date per order
	orderLeads = combine_order_leads(oldLeads=orderLeads.copy(), newLeads=freshLeads.copy())

	newMOdf = analyze_schedule(newMOdf=newMOdf.copy(),
							   orderLeads=orderLeads.copy(),
							   modf=modf.copy(),
							   mfgCenters=mfgCenters.copy(),
							   dateList=dateList.copy(),
							   orderRunTime=orderRunTime,
							   leadTimes=leadTimes.copy())
	return(newMOdf.copy())







