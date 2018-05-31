__author__ = 'Jack'

import os
import pandas as pd
import numpy as np


from IPython.core.debugger import Tracer
debug_here = Tracer()

import logging
logging.basicConfig(filename='example.log',level=logging.DEBUG)

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
def create_date_list(todayTimestamp=pd.Timestamp.today(), dailyLabor=10):
	# create a list of dates starting with today.
	dateList = pd.DataFrame({'StartDate': pd.date_range(todayTimestamp, periods=5000, freq='1D'),
							 'DaysFromStart': np.nan,
							 'AvailableLabor': np.nan})

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
	moLinesLabor = pd.merge(moFgOnly.copy(), mfgCenters[['PART','Mfg Center','Setup','LaborPer']].copy(), how='left', on='PART')

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
### replacing this with sched_with_date_limits.  It does the same thing but needs an earliest schedule date column to check.
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
	### Currently phantom orders are placed a day before the order (with the shortage) will finish.  So
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

# checks a schedule for any orders scheduled ahead of their earliest allowed date
# if it finds something, it runs another schedule loop and checks again until no issues are remaining
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
		newMOdf = schedule_loop(modf=modf.copy(),
								orderLeads=orderLeads.copy(),
								mfgCenters=mfgCenters.copy(),
								dateList=dateList.copy(),
								orderRunTime=orderRunTime,
								leadTimes=leadTimes.copy())
		return(newMOdf.copy())
	else:
		print('no schedule issues found')
		return(newMOdf.copy())

# adjusts schedule dates and runs a sim.  Uses analyze_schedule() to check its result.
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


# Trying something with multiple labor types, not totally into this though.  requires hard coding each type.
def analyze_schedule_labor_types(newMOdf, orderLeads, modf, mfgCenters, dateList, orderRunTime, leadTimes, dateListProLine, dateListRacking, dateListPCB, dateListLabels, dateListKitting, dateListShipping, dateListCableAssy):
	print('in analyze_schedule')
	tempMOdf = newMOdf.sort_values(by=['ORDER','DATESCHEDULED'], ascending=[True, True]).copy()
	tempMOdf.drop_duplicates('ORDER', keep='first', inplace=True)
	checkSched = pd.merge(tempMOdf[['ORDER','DATESCHEDULED']].copy(),
						  orderLeads[['ORDER','EarliestScheduleDate']].copy(),
						  how='left', on='ORDER')
	checkSched['TimeDiff'] = np.nan
	# need to convert 'DATESCHEDULED' column to datetime or it will register as a float and error out in comparison
	checkSched['DATESCHEDULED'] = pd.to_datetime(checkSched['DATESCHEDULED'].copy())
	# if there are any instances where a line is scheduled before it's supposed to, set a value to the TimeDiff column
	for each in range(0, len(checkSched)):
	    if checkSched['DATESCHEDULED'].iat[each] < checkSched['EarliestScheduleDate'].iat[each]:
	        checkSched['TimeDiff'] = 'here'
	        print(checkSched['ORDER'].iat[each])
	# if there is a value set to the TimeDiff column, then the schedule loop needs to run again
	if len(checkSched['TimeDiff'].dropna()) != 0:
		newMOdf = schedule_loop_labor_types(modf=modf.copy(),
								  orderLeads=orderLeads.copy(),
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
		# return the scheduled orders
		return(newMOdf.copy())
	else:
		print('no schedule issues found')
		return(newMOdf.copy())

# adjusts schedule dates and runs a sim.  Uses analyze_schedule() to check its result.
def schedule_loop_labor_types(modf, orderLeads, mfgCenters, dateList, orderRunTime, leadTimes, dateListProLine, dateListRacking, dateListPCB, dateListLabels, dateListKitting, dateListShipping, dateListCableAssy):
	print('in schedule_loop')
	### CREATE NEW SCHEDULE ###

	# save a new copy of the modf with longest leads added
	leadMOdf = pd.merge(modf.copy(), orderLeads[['ORDER','EarliestScheduleDate']].copy(), how='left', on='ORDER')
	moLinesLabor = pre_schedule_prep(modf=leadMOdf, mfgCenters=mfgCenters.copy())

	outputScheduleProLine = sched_with_date_limits(orderPriority=moLinesLabor[moLinesLabor['Mfg Center'] == 'Pro Line'].copy(), dateList=dateListProLine.copy())
	outputScheduleRacking = sched_with_date_limits(orderPriority=moLinesLabor[moLinesLabor['Mfg Center'] == 'Racking'].copy(), dateList=dateListRacking.copy())
	outputSchedulePCB = sched_with_date_limits(orderPriority=moLinesLabor[moLinesLabor['Mfg Center'] == 'PCB'].copy(), dateList=dateListPCB.copy())
	outputScheduleLabels = sched_with_date_limits(orderPriority=moLinesLabor[moLinesLabor['Mfg Center'] == 'Labels'].copy(), dateList=dateListLabels.copy())
	outputScheduleKitting = sched_with_date_limits(orderPriority=moLinesLabor[moLinesLabor['Mfg Center'] == 'Kitting'].copy(), dateList=dateListKitting.copy())
	outputScheduleShipping = sched_with_date_limits(orderPriority=moLinesLabor[moLinesLabor['Mfg Center'] == 'Shipping'].copy(), dateList=dateListShipping.copy())
	outputScheduleCableAssy = sched_with_date_limits(orderPriority=moLinesLabor[moLinesLabor['Mfg Center'] == 'Cable Assembly'].copy(), dateList=dateListCableAssy.copy())

	outputScheduleProLine.drop_duplicates('ORDER', keep='last', inplace=True)
	outputScheduleRacking.drop_duplicates('ORDER', keep='last', inplace=True)
	outputSchedulePCB.drop_duplicates('ORDER', keep='last', inplace=True)
	outputScheduleLabels.drop_duplicates('ORDER', keep='last', inplace=True)
	outputScheduleKitting.drop_duplicates('ORDER', keep='last', inplace=True)
	outputScheduleShipping.drop_duplicates('ORDER', keep='last', inplace=True)
	outputScheduleCableAssy.drop_duplicates('ORDER', keep='last', inplace=True)

	newSchedule = pd.concat([outputScheduleProLine,
		   				   	 outputScheduleRacking,
		   				   	 outputSchedulePCB,
		   				   	 outputScheduleLabels,
		   				   	 outputScheduleKitting,
		   				   	 outputScheduleShipping,
		   				   	 outputScheduleCableAssy])

	# outputSchedule = sched_with_date_limits(orderPriority=moLinesLabor.copy(),
	#                                             dateList=dateList.copy())
	# use the last scheduled FG in an order to save a new schedule
	# newSchedule = outputSchedule.drop_duplicates('ORDER', keep='last').copy()

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

	newMOdf = analyze_schedule_labor_types(newMOdf=newMOdf.copy(),
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
	return(newMOdf.copy())







#############################################################################
# REMAKE
#############################################################################

# this function is for setting new earliest start dates for orders.
# it will not set a date for a specific order if it is already set for a later date.
def attempt_adjust_earliest_start_date(order, newDate, workCenter, earliestDateList):
	earliestDateList.reset_index(drop=True, inplace=True)
	dateListCheck = earliestDateList[earliestDateList['ORDER'] == order].copy()
	if len(dateListCheck) > 0: # if it has no rows, then the order just needs to be appended
		if dateListCheck['startDateLimit'].iat[0] < newDate: # if not then it will keep the later date
			rowIndex = earliestDateList.loc[earliestDateList['ORDER'] == order].index[0]
			earliestDateList.at[rowIndex, 'startDateLimit'] = newDate
	else: # adds a fresh line with the order and its date limit
		tempDateDF = pd.DataFrame(data={'ORDER': [order],
									    'startDateLimit': [newDate],
									    'MfgCenter': [workCenter]})
		earliestDateList = earliestDateList.copy().append(tempDateDF.copy(), sort=False)
	earliestDateList.reset_index(drop=True, inplace=True)
	return earliestDateList.copy()

# this function is for bumping priority levels higher for orders needed as dependencies
# it will not change priority if it is already higher than the reference order
def attempt_adjust_order_priority(adjustOrder, rootOrder, orderPriority):
	orderPriority.reset_index(drop=True, inplace=True)
	# get the priority levels of each order
	adjustOrderFrame = orderPriority[orderPriority['ORDER'] == adjustOrder].copy()
	adjustOrderPri = adjustOrderFrame['Priority'].iat[0]
	rootOrderFrame = orderPriority[orderPriority['ORDER'] == rootOrder].copy()
	rootOrderPri = rootOrderFrame['Priority'].iat[0].copy()
	# if the adjustable order is lower priority (higher numerically), set it just above the root order
	if adjustOrderPri > rootOrderPri:
		rowIndex = orderPriority.loc[orderPriority['ORDER'] == adjustOrder].index[0]
		orderPriority.at[rowIndex, 'Priority'] = rootOrderPri - 0.5
		# sort the orders by priority and refresh the list to consecutive integers
		orderPriority.sort_values('Priority', ascending=True, inplace=True)
		pri = 1
		for index in orderPriority.index:
			orderPriority.at[index, 'Priority'] = pri
			pri += 1
		orderPriority.reset_index(drop=True, inplace=True)
	else:
		# if the adjust order priority is already higher than the root order priority then just sort.
		# HEY there is a chance that this also requires a refreshed priority list
		orderPriority.sort_values('Priority', ascending=True, inplace=True)
		# pri = 1
		# for index in orderPriority.index:
		# 	orderPriority.at[index, 'Priority'] = pri
		# 	pri += 1
	return orderPriority.copy()

# this function will add a dependency to the existing list
def set_dependency(order, dependency, dependencyDF):
	tempDF = pd.DataFrame(data={'ORDER': [order],
						   		'dependency': [dependency]})
	dependencyDF = dependencyDF.copy().append(tempDF.copy(), sort=False)
	return dependencyDF.copy()

# this function schedules the current order during a loop
def schedule_order(currentOrder, orderPriority, laborRequired, laborScheduled, dateListCenter, scheduledOrders, dependencies, earliestDateAllowed, unscheduledLines, scheduledLines, startDate):
	# schedule the current order at time it would finish if started at attempted date
	# if currentOrder == 'P2':
	# 	debug_here()
	orderToSchedule = orderPriority[orderPriority['ORDER'] == currentOrder].copy()
	# laborRequired = orderToSchedule['LaborRequired'].iat[0] # unnecessary because it's still saved from earlier
	# laborScheduled # also set at the beginning of the loop
	totalLabor = laborRequired + laborScheduled
	laborDateRef = dateListCenter[dateListCenter['AvailableLabor'] >= totalLabor].copy()
	if len(laborDateRef) == 0:
		print('THIS IS ATTEMPTING TO SCHEDULE A FEW YEARS IN THE FUTURE')
		print('check the labor needed for this order')
		print('labor previously scheduled: ' + str(laborScheduled))
		print('labor required: ' + str(laborRequired))
		print('order is: ')
		print(orderToSchedule)
		print(unscheduledLines[unscheduledLines['ORDER'] == currentOrder])
		finishDate = laborDateRef['StartDate'].iat[0] # This line should error out because the dataFrame is empty
	finishDate = laborDateRef['StartDate'].iat[0]
	orderToSchedule['DATESCHEDULED'] = finishDate
	orderToSchedule['STARTDATE'] = startDate
	scheduledOrders = scheduledOrders.copy().append(orderToSchedule.copy(), sort=False)

	orderPriority = orderPriority[orderPriority['ORDER'] != currentOrder].copy()

	# HEY might need to add finishDate as earliest date limits to orders with this dependency, not sure
	# adjusting earliest date limits of orders with current order as dependency
	dependentList = dependencies[dependencies['dependency'] == currentOrder].copy()
	tempWorkCenterReference = orderPriority.copy().append(scheduledOrders.copy(), sort=False)
	for depOrder in dependentList['ORDER']:
		tempWCDF = tempWorkCenterReference[tempWorkCenterReference['ORDER'] == depOrder].copy()
		workCenter = tempWCDF['MfgCenter'].iat[0]
		earliestDateAllowed = attempt_adjust_earliest_start_date(order=depOrder,
								   						 		 newDate=finishDate,
								   						 		 workCenter=workCenter,
								   						 		 earliestDateList=earliestDateAllowed)
	dependencies = dependencies[dependencies['dependency'] != currentOrder].copy()

	linesToSchedule = unscheduledLines[unscheduledLines['ORDER'] == currentOrder].copy()
	linesToSchedule['DATESCHEDULED'] = finishDate
	scheduledLines = scheduledLines.copy().append(linesToSchedule.copy(), sort=False)

	unscheduledLines = unscheduledLines[unscheduledLines['ORDER'] != currentOrder].copy()

	return(orderPriority.copy(),
		   scheduledOrders.copy(),
		   dependencies.copy(),
		   earliestDateAllowed.copy(),
		   unscheduledLines.copy(),
		   scheduledLines.copy())

# this function creates fake order numbers for Phantom orders
def generate_fake_order(fakeOrderIter):
	fakeOrderIter += 1
	newOrder = "P" + str(fakeOrderIter)
	return(newOrder, fakeOrderIter)

# this function adds a part to the Series tracking parts with no labor info
def add_to_missing_labor(part, missingLabor):
	missingLabor = missingLabor.append(pd.DataFrame(data={'PART': [part]}), sort=False)
	return missingLabor

# this function adds a part to the Series tracking parts with no BOMs
def add_to_missing_bom(part, missingBOM):
	missingBOM = missingBOM.append(pd.DataFrame(data={'PART': [part]}), sort=False)
	return missingBOM

"""Converts quantities to the default unit of measure for each part
    uomid 1 is 'ea'
    uomid 2 is 'ft'
    uomid 7 is 'in' """
def fix_uom(orgdf):
	orgdf.reset_index(drop=True, inplace=True)
	uomIssues = orgdf[orgdf['BOMUOM'] != orgdf['PARTUOM']].copy()
	for index, row in uomIssues.iterrows():
		origQty = row['QTY']
		if (row['BOMUOM'] == 1 and row['PARTUOM'] == 2): # if BOM is 'ea' and part is 'ft' then multiply by 2
			orgdf['QTY'].at[index] = origQty * 2
			# orgdf.set_value(index, 'QTY', (row['QTY'] * 2))
		elif (row['BOMUOM'] == 2 and row['PARTUOM'] == 1): # if BOM is 'ft' and part is 'ea' then divide by 2
			orgdf['QTY'].at[index] = origQty / 2
			# orgdf.set_value(index, 'QTY', (row['QTY'] / 2))
		elif (row['BOMUOM'] == 2 and row['PARTUOM'] == 7): # if BOM is 'ft' and part is 'in' then multiply by 12
			orgdf['QTY'].at[index] = origQty * 12
			# orgdf.set_value(index, 'QTY', (row['QTY'] * 12))
		elif (row['BOMUOM'] == 7 and row['PARTUOM'] == 2): # if BOM is 'in' and part is 'ft' then divide by 12
			orgdf['QTY'].at[index] = origQty / 12
			# orgdf.set_value(index, 'QTY', (row['QTY'] / 12))
	return(orgdf.copy())

"""Adds an inventory counter on the timeline sheet"""
def add_inv_counter(inputTimeline, backdate, invdf):
	timeorder = inputTimeline.sort_values(by=['PART', 'DATESCHEDULED'], ascending=[True, True]).copy()  # Sort the list of inventory actions
	timeorder.reset_index(drop=True, inplace=True)  # reset the index, not super necessary but I like it
	partlist = pd.merge(timeorder.copy(), invdf.copy(), on='PART', how='left')  # merge the Fishbowl inventory onto the part lines
	partlist['INV'].fillna(0, inplace=True)  # anything missing a value in the new inventory column should be 0
	resultdf = pd.DataFrame()  # to be used as the output with a counter attached
	colHeaders = list(partlist)  # store the column headers
	# backdate = '1999-12-31 00:00:00'  # this is an arbitrary date for starting inventory, is now input as a parameter above
	orderType = 'Starting Inventory'  # this will be the order type label
	for each in timeorder['PART'].unique():  # for each part in the list of actions
		currentPart = each  # I just did this for readability but could be removed with minor adjustments
		currentPartOrders = partlist[partlist['PART'] == currentPart].copy()  # make a dataFrame of orders with just the current part
		tempdf = pd.DataFrame(columns=colHeaders, index=[0])  # make a temporary dataFrame with one empty line and use the column headers
		tempdf[['ORDERTYPE', 'PART', 'DATESCHEDULED']] = [orderType, currentPart, backdate]  # make this line the starting inventory line
		tempdf = tempdf.append(currentPartOrders, ignore_index=True, sort=False)  # append the current part's orders to the starting line
		tempdf['INV'].at[0] = tempdf['INV'].iloc[1]
		# tempdf.set_value(index=0, col='INV', value= tempdf['INV'].iloc[1])  # this references the inventory on the other columns to set the starting inventory
		ind = 1  # This is going to iterate through the index or rows
		while ind < len(tempdf):  # while this indexer is less than the length
			tempdf['INV'].at[ind] = (tempdf['INV'].iloc[ind-1] + tempdf['QTYREMAINING'].iloc[ind])
			# tempdf.set_value(ind, 'INV', (tempdf['INV'].iloc[ind-1] + tempdf['QTYREMAINING'].iloc[ind]))  # set the next inventory value by adding the order amount to the previous inventory value
			ind += 1  # step up the indexer
		resultdf = resultdf.append(tempdf.copy(), ignore_index=True, sort=False)  # store this as a result
	return resultdf  # results are the new demand dataFrame