__author__ = 'Jack'

import pandas as pd
import numpy as np


from IPython.core.debugger import Tracer
debug_here = Tracer()

import logging
logging.basicConfig(filename='example.log',level=logging.DEBUG)


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
	# if currentOrder == 'P57':
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
	if laborRequired == 0: # fixes bug where startDate can occur after finishDate
		startDate = finishDate
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