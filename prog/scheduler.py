__author__ = 'Jack'

import os
import pandas as pd
import numpy as np

def test_sched(x):
	print(x)


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


# create a new schedule based on the current MO dates and available labor by date
def run_auto_schedule(modf, mfgCenters, dateList):
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

	# replace nulls with 0 for maths.  Probably not necessary, didn't test.
	moLinesLabor.fillna(0, inplace=True)

	# create a column for the total labor required for each order
	moLinesLabor['LaborRequired'] = moLinesLabor['Setup'] + (moLinesLabor['LaborPer'] * moLinesLabor['QTYREMAINING'])

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
def run_auto_schedule_with_limitations(modf, mfgCenters, dateList):
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

	# replace nulls with 0 for maths.  Probably not necessary, didn't test.
	moLinesLabor.fillna(0, inplace=True)

	# create a column for the total labor required for each order
	moLinesLabor['LaborRequired'] = moLinesLabor['Setup'] + (moLinesLabor['LaborPer'] * moLinesLabor['QTYREMAINING'])

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
