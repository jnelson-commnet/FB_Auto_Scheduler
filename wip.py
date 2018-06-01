__author__ = 'Jack'

### IMPORTS ###

import os
import sys
import pandas as pd
import numpy as np

from prog import scheduler as sch

import dependencies as dp

from IPython.core.debugger import Tracer
debug_here = Tracer()

import logging

logging.basicConfig(filename='example.log',level=logging.DEBUG)
logging.debug('---------------------------------------------------------------------------------------------------------')


# save current working directory as homey
homey = os.path.abspath(os.path.dirname(__file__))
# homey = os.getcwd() # works in jupyter notebook

# set directory paths
dataPath = os.path.join(homey, 'data')
# progPath = os.path.join(homey, 'prog')
# simPath = os.path.join(homey, 'FB_Sim')
# forcPath = os.path.join(simPath, 'ForecastRedoux')
# this should probably be moved out of the simulator and into the main sql area, where that ends up
# sqlPath = os.path.join(forcPath, 'SQL')
queryPath = os.path.join(dataPath, 'query')

# set paths to excel files
# forecastFilename = os.path.join(dataPath, 'RegularForecast.xlsx')
mfgCentersFilename = os.path.join(dataPath, 'MfgCenters.xlsx')
moFilename = os.path.join(dataPath, 'MOs.xlsx')
laborAvailFilename = os.path.join(dataPath, 'LaborAvailablePerDay.xlsx')
leadFilename = os.path.join(dataPath, 'LeadTimes.xlsx')
invFilename = os.path.join(dataPath, 'INVs.xlsx')
soFilename = os.path.join(dataPath, 'SOs.xlsx')
poFilename = os.path.join(dataPath, 'POs.xlsx')
partFilename = os.path.join(dataPath, 'Parts.xlsx')
descFilename = os.path.join(dataPath, 'Descs.xlsx')
bomFilename = os.path.join(dataPath, 'BOMs.xlsx')
finalSchedFilename = os.path.join(homey, 'finalSchedule.xlsx')
missingFilename = os.path.join(homey, 'missing.xlsx')

### QUERIES ###

# Live server:
# sys.path.insert(0, 'Z:\Python projects\FishbowlAPITestProject')
# import connecttest

# print('queries started')

# myresults = connecttest.create_connection(queryPath, 'leadtimequery.txt')
# myexcel = connecttest.makeexcelsheet(myresults)
# connecttest.save_workbook(myexcel, dataPath, 'LeadTimes.xlsx')

# myresults = connecttest.create_connection(queryPath, 'mfgcenterquery.txt')
# myexcel = connecttest.makeexcelsheet(myresults)
# connecttest.save_workbook(myexcel, dataPath, 'MfgCenters.xlsx')

# myresults = connecttest.create_connection(queryPath, 'BOMQuery.txt')
# myexcel = connecttest.makeexcelsheet(myresults)
# connecttest.save_workbook(myexcel, dataPath, 'BOMs.xlsx')

# myresults = connecttest.create_connection(queryPath, 'DescQuery.txt')
# myexcel = connecttest.makeexcelsheet(myresults)
# connecttest.save_workbook(myexcel, dataPath, 'Descs.xlsx')

# myresults = connecttest.create_connection(queryPath, 'INVQuery.txt')
# myexcel = connecttest.makeexcelsheet(myresults)
# connecttest.save_workbook(myexcel, dataPath, 'INVs.xlsx')

# myresults = connecttest.create_connection(queryPath, 'MOQueryRedoux.txt')
# myexcel = connecttest.makeexcelsheet(myresults)
# connecttest.save_workbook(myexcel, dataPath, 'MOs.xlsx')

# myresults = connecttest.create_connection(queryPath, 'PartQuery.txt')
# myexcel = connecttest.makeexcelsheet(myresults)
# connecttest.save_workbook(myexcel, dataPath, 'Parts.xlsx')

# myresults = connecttest.create_connection(queryPath, 'POQuery.txt')
# myexcel = connecttest.makeexcelsheet(myresults)
# connecttest.save_workbook(myexcel, dataPath, 'POs.xlsx')

# myresults = connecttest.create_connection(queryPath, 'SOQuery.txt')
# myexcel = connecttest.makeexcelsheet(myresults)
# connecttest.save_workbook(myexcel, dataPath, 'SOs.xlsx')

# myresults = connecttest.create_connection(queryPath, 'LABQuery.txt')
# myexcel = connecttest.makeexcelsheet(myresults)
# connecttest.save_workbook(myexcel, dataPath, 'LaborAvailablePerDay.xlsx')

print('queries finished')

### GET DATA ###

print('retrieving data')

# save mfgCenters as df, includes MFG Center assignments and Setup/labor time estimates
mfgCenters = pd.read_excel(mfgCentersFilename, header=0)

# save current Manufacture Orders
moDF = pd.read_excel(moFilename, header=0)
moDF['DATESCHEDULED'] = pd.to_datetime(moDF['DATESCHEDULED'].copy())
moDF['ORDER'] = moDF['ORDER'].astype(str)
moDF['MOSCHEDULEDATE'] = pd.to_datetime(moDF['MOSCHEDULEDATE'].copy())
moDF['MOISSUEDATE'] = pd.to_datetime(moDF['MOISSUEDATE'].copy())
moPriority = moDF.copy() # saving copy for priority assorting
moDF = moDF[['ORDER','ITEM','ORDERTYPE','PART','QTYREMAINING','DATESCHEDULED','PARENT']].copy()

# save lead time estimates
leadTimes = pd.read_excel(leadFilename, header=0)
# the lead time estimates are drawing from a couple fields
# the following section sorts out the preferred lead time for each part and adds it to the "LeadTimes" column
leadTimes.sort_values(by=['PART','DefaultVendor','LastDate'], ascending=[True,False,False], inplace=True)
leadTimes.drop_duplicates('PART', keep='first', inplace=True)
leadTimes['LeadTimes'] = np.nan
x=0
while x < len(leadTimes):
	if leadTimes['RealLeadTime'].iat[x] > 0:
		leadTimes['LeadTimes'].iat[x] = leadTimes['RealLeadTime'].iat[x]
	elif leadTimes['VendorLeadTime'].iat[x] > 0:
		leadTimes['LeadTimes'].iat[x] = leadTimes['VendorLeadTime'].iat[x]
	x += 1
leadTimes = leadTimes[['PART','Make/Buy','AvgCost','LeadTimes']].copy()
### this is a bandaid, I think there will be problems with NAN values later.  Need to figure out eventually.
leadTimes.fillna(10, inplace=True)

# save current BOMs
bomDF = pd.read_excel(bomFilename, header=0)
# query brings all finished good and raw good lines as positive quanities.
# change the raw goods to negative for easier order creating throughout
fgBomDF = bomDF[bomDF['FG'] == 10].copy()
rawBomDF = bomDF[bomDF['FG'] == 20].copy()
rawBomDF['QTY'] = rawBomDF['QTY'].copy() * (-1)
bomDF = fgBomDF.copy().append(rawBomDF.copy(), sort=False)
bomDF.sort_values(by='BOM', inplace=True)
bomDF = sch.fix_uom(bomDF.copy())
bomDF.reset_index(drop=True, inplace=True)

# save current part descriptions
descDF = pd.read_excel(descFilename, header=0)

# save current inventory
invDF = pd.read_excel(invFilename, header=0)
invDF['INV'] = invDF['INV'].round(2) # just getting the floats out.

# save current labor availability
laborDF = pd.read_excel(laborAvailFilename, header=0)
# use this laborDF to create a dictionary of dateLists with production centers as the keys.
# the dateLists will be used to track labor available at a given time.
dateListDict = {}
todayTimestamp = pd.Timestamp.today()
for x in range(0, len(laborDF)):
	labType = laborDF['LaborType'].iat[x]
	hoursPerDay = laborDF['HoursPerDay'].iat[x]
	centerDateList = sch.create_date_list(todayTimestamp=todayTimestamp, dailyLabor=hoursPerDay)
	dateListDict[labType] = centerDateList.copy()
referenceDateList = sch.create_date_list(todayTimestamp=todayTimestamp, dailyLabor=1)

# save current parts list - doubt this is needed, maybe combine with something else like desc and avgcost
partDF = pd.read_excel(partFilename, header=0)

# save current Sales Orders
soDF = pd.read_excel(soFilename, header=0)
soDF['DATESCHEDULED'] = pd.to_datetime(soDF['DATESCHEDULED'].copy())
soDF['ORDER'] = soDF['ORDER'].astype(str)
soDF['ISSUED'] = pd.to_datetime(soDF['ISSUED'].copy())
soDF['CUSTDELIVDATE'] = pd.to_datetime(soDF['CUSTDELIVDATE'].copy())
soPriority = soDF.drop_duplicates('ORDER', keep='first').copy() # saving for priority sorting later
soDF = soDF[['ORDER','ITEM','ORDERTYPE','PART','QTYREMAINING','DATESCHEDULED','PARENT']].copy()

# save current Purchase Orders
poDF = pd.read_excel(poFilename, header=0)
poDF['DATESCHEDULED'] = pd.to_datetime(poDF['DATESCHEDULED'].copy())
poDF.sort_values(by='DATESCHEDULED', ascending=True, inplace=True) # not necessary but easier for debug
poDF['ORDER'] = poDF['ORDER'].astype(str)

print('data retrieved')


# fakeOrderIter is used to create fake orders throughout the script
fakeOrderIter = 0

# these are Series used to track missing labor info and BOMs
missingLabor = pd.DataFrame(data={'PART':[]})
missingBOM = pd.DataFrame(data={'PART':[]})


### Sort Orders by Priority ###

# need a list of orders and way to prioritize them, can be handled a few ways.
# the orderPriority list needs to carry the MfgCenter responsible for the order and labor required.
# SOs all require shipping so start with that ...
# soPriority = soDF.drop_duplicates('ORDER', keep='first').copy() # handled above
soPriority.sort_values(by=['PRIORITY','CUSTDELIVDATE','ISSUED'], ascending=[True,True,True], inplace=True)
soPriority = soPriority[['ORDER','DATESCHEDULED']].copy()
soPriority['MfgCenter'] = 'Shipping' # assigning all to shipping dept
# HEY THIS IS WEIRD, it's a hard coded labor required per SO.
# There should be some calculation of time required for each line or something to that effect.
# For now I'm making the assumption that every SO requires 1 hour of shipping labor to fulfill.
shipLaborRequired = 1
soPriority['LaborRequired'] = shipLaborRequired
# now we need to get each WO with MfgCenter and labor required
moPriority['PRIORITY'] = moPriority['PRIORITY'].fillna('20-Planned') # default to planned for priority states not yet set
moPriority = moPriority[moPriority['QTYREMAINING'] > 0].copy() # reducing WO lines to positive quantities, probably all FGs
moPriority = pd.merge(moPriority.copy(), mfgCenters[['PART','MfgCenter','LaborPer']].copy(), how='left', on='PART') # attach labor info where possible
# HEY THIS IS WEIRD the MO order labor required is based on labor per * qty produced, but labor per is a BOM reference, so some builds might be off
moPriority['LaborRequired'] = moPriority['LaborPer'] * moPriority['QTYREMAINING'] # calculate labor for order
moPriority.sort_values(by='LaborRequired', ascending=False, inplace=True) # bring highest labor to top
moPriority.drop_duplicates('ORDER', keep='first', inplace=True) # drop duplicate order lines and keep highest labor available
# bandaid for missing MfgCenter and LaborRequired
moNullCheck = moPriority[moPriority['MfgCenter'].isnull()].copy()
moPriority = moPriority[moPriority['MfgCenter'].notnull()].copy()
# adding Pro line as area responsible for anything unknown, probably not a good idea
moNullCheck['MfgCenter'] = 'Unknown'
for missingPart in moNullCheck['PART']:
	missingLabor = sch.add_to_missing_labor(part=missingPart, missingLabor=missingLabor)
moPriority = moPriority.copy().append(moNullCheck.copy(), sort=False)
# sorting by custom field priority and then by various schedule dates
moPriority.sort_values(by=['PRIORITY','MOSCHEDULEDATE','MOISSUEDATE','DATESCHEDULED'], ascending=[True,True,True,True], inplace=True)
moPriority = moPriority[['ORDER','DATESCHEDULED','MfgCenter','LaborRequired']].copy()

# now create order priority by appending SO and MO
orderPriority = soPriority.copy().append(moPriority.copy(), sort=False)
orderPriority.reset_index(drop=True, inplace=True)
orderPriority['Priority'] = np.nan
pri = 1
for index in orderPriority.index:
	orderPriority.at[index, 'Priority'] = pri
	pri += 1

# HEY, filling the empty labor sets with 0 might not be a good idea, either handle missing labor better elsewhere or log these before replacing them
orderPriority['LaborRequired'] = orderPriority['LaborRequired'].fillna(0)

ordPriHeaders = list(orderPriority.copy())
ordPriHeaders.append('STARTDATE')
scheduledOrders = pd.DataFrame(columns=ordPriHeaders) # this will store anything scheduled and removed from orderPriority

# create a dataFrame for tracking earliest start date allowed limitations
earliestDateAllowed = pd.DataFrame(columns=['ORDER','startDateLimit','MfgCenter'])

# create a dataFrame for tracking order dependency, aka any orders needing to be scheduled before this one
dependencies = pd.DataFrame(columns=['ORDER','dependency'])

print('created orderPriority')

# this loop attempts to schedule an order from the order priority list
def order_schedule_attempt(orderPriority,
				   		   scheduledOrders,
				   		   scheduledLines,
				   		   unscheduledLines,
				   		   earliestDateAllowed,
				   		   dependencies,
				   		   dateListDict,
				   		   invDF,
				   		   partDF,
				   		   fakeOrderIter,
				   		   mfgCenters,
				   		   bomDF,
				   		   leadTimes,
				   		   referenceDateList,
				   		   missingLabor,
				   		   missingBOM):
	scheduleSuccess = False
	x = 0
	# remove orders with dependencies to avoid iterating through each to check
	limitOrderPriority = orderPriority.copy()
	limitOrderPriority = limitOrderPriority.copy().append(dependencies.copy(), sort=False)
	limitOrderPriority.drop_duplicates('ORDER', keep=False, inplace=True)
	limitOrderPriority = limitOrderPriority[['ORDER','DATESCHEDULED','MfgCenter','LaborRequired','Priority']].copy()
	# remove orders that will be date limited for their work center's next available date
	tempWorkCenterList = limitOrderPriority['MfgCenter'].unique()
	for workCenter in tempWorkCenterList:
		# for each work area, get the earliest schedule date opportunity
		laborUsed = 0
		prevSchedLabor = scheduledOrders[scheduledOrders['MfgCenter'] == workCenter].copy()
		if len(prevSchedLabor) > 0:
			laborUsed = prevSchedLabor['LaborRequired'].sum()
		availableLabor = dateListDict[workCenter].copy()
		availableLabor = availableLabor[availableLabor['AvailableLabor'] > laborUsed].copy()
		dateAttemptStart = availableLabor['StartDate'].iat[0]
		# split out this work area's order priority list
		# workCenterPriority = limitOrderPriority[limitOrderPriority['MfgCenter'] == workCenter].copy()
		# limitOrderPriority = limitOrderPriority[limitOrderPriority['MfgCenter'] != workCenter].copy()
		# get list of date limited orders for this work area
		dateLimitedOrders = earliestDateAllowed[earliestDateAllowed['MfgCenter'] == workCenter].copy()
		dateLimitedOrders = dateLimitedOrders[dateLimitedOrders['startDateLimit'] >= dateAttemptStart].copy()
		limitOrderPriority = limitOrderPriority.copy().append(dateLimitedOrders.copy(), sort=False)
		limitOrderPriority.drop_duplicates('ORDER', keep=False, inplace=True)
	limitOrderPriority = limitOrderPriority[['ORDER','DATESCHEDULED','MfgCenter','LaborRequired','Priority']].copy()
	limitOrderPriority.dropna(inplace=True)

	while x < len(limitOrderPriority):
		# debug_here()
		# if len(limitOrderPriority) > 1345:
			# debug_here()
		print(str(x) + ' of ' + str(len(limitOrderPriority)))
		logging.debug(str(x) + ' of ' + str(len(limitOrderPriority)) + ' orderPriority is ' + str(len(orderPriority)))
		limitOrderPriority.reset_index(drop=True, inplace=True) # might need to do this to make sure rows nums and indexes match for ease


		# Check if starting inventory plus all scheduled orders results in any negatives:
		# 	error out if true
		currentOrderSum = scheduledLines[['PART','QTYREMAINING']].copy().groupby('PART').sum()
		currentOrderSum.reset_index(inplace=True)
		currentOrderSum.rename(columns={'QTYREMAINING':'INV'}, inplace=True)
		currentInvSum = invDF.copy().append(currentOrderSum.copy(), sort=False)
		currentInvSum = currentInvSum.groupby('PART').sum()
		currentInvSum.reset_index(inplace=True)
		negativeInv = currentInvSum[currentInvSum['INV'] < 0]
		if len(negativeInv) > 0: # if any inventory lines are negative, this will be true
			# print(negativeInv)
			# print('HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHOOOOOOOOOOOOOOOOOOOOOOOOOOOO') # I think this will throw an error
			pass

		currentOrder = limitOrderPriority['ORDER'].iat[x] # will need to check if there are restrictions for this order
		# if len(limitOrderPriority) == 3:
		# if 'P2002' in scheduledOrders['ORDER'].unique():
		# 	if currentOrder == '26367:051':
		# 		debug_here()
		# ?Check first pri order for earliest available schedule time according to labor group (probably Shipping on first loop)
		workCenter = limitOrderPriority['MfgCenter'].iat[x] # production area for current order
		laborRequired = limitOrderPriority['LaborRequired'].iat[x] # maybe not necessary yet?
		laborUsed = 0
		print(workCenter)
		prevSchedLabor = scheduledOrders[scheduledOrders['MfgCenter'] == workCenter].copy()
		if len(prevSchedLabor) > 0:
			laborUsed = prevSchedLabor['LaborRequired'].sum()
		logging.debug('workCenter: ' + str(workCenter) + ' for order: ' + str(currentOrder))
		availableLabor = dateListDict[workCenter].copy()
		availableLabor = availableLabor[availableLabor['AvailableLabor'] > laborUsed].copy()
		dateAttemptStart = availableLabor['StartDate'].iat[0] # this should be the start date this order will try to schedule
		# laborAvailable = availableLabor['AvailableLabor'].iat[0] # This doesn't seem to be necessary, actually needed laborUsed



		# if there is an earliest start date limit and it's later than the attempted start,
		# then move on to the next order in the priority list
		orderDateLimit = earliestDateAllowed[earliestDateAllowed['ORDER'] == currentOrder].copy()
		if len(orderDateLimit) > 0:
			currentDateLimit = orderDateLimit['startDateLimit'].iat[0]
			if dateAttemptStart < currentDateLimit:
				x += 1
				logging.debug('date limited')
				continue

		# if currentOrder == '51539/41209':
		# 	debug_here()

		# there might be an issue with this next section.
		# if a dependency is scheduled for later than the current attempt,
		# then this order can't be scheduled yet.
		# can fix this by making any order that exists as a dependecy affect other orders' earliest start dates.
		# debug_here()
		# before entering while loop, all orders with dependencies are removed, so this should never trigger
		orderDependencyLimit = dependencies[dependencies['ORDER'] == currentOrder].copy()
		if len(orderDependencyLimit) > 0:
			x += 1
			logging.debug('order dependent, something went wrong')
			continue

		# Make an Inventory Counter:
		# collect a sum of all scheduled positive orders up to the current schedule date
		orderLinesToDate = scheduledLines[scheduledLines['DATESCHEDULED'] <= dateAttemptStart].copy()
		positiveOrderLinesToDate = orderLinesToDate[orderLinesToDate['QTYREMAINING'] > 0].copy()
		positiveOrderLinesToDate = positiveOrderLinesToDate[['PART','QTYREMAINING']].copy().groupby('PART').sum()
		positiveOrderLinesToDate.reset_index(inplace=True)

		# collect all negative orders including those scheduled later than the current attempted date
		negativeOrderLines = scheduledLines[scheduledLines['QTYREMAINING'] < 0].copy()
		negativeOrderLines = negativeOrderLines[['PART','QTYREMAINING']].copy().groupby('PART').sum()
		negativeOrderLines.reset_index(inplace=True)

		# add the orders to starting inventory to get a snapshot of inventory totals relevant to this schedule attempt
		invCounter = invDF.rename(columns={'INV':'QTYREMAINING'}).copy()
		invCounter = invCounter.copy().append(positiveOrderLinesToDate.copy().append(negativeOrderLines.copy(), sort=False), sort=False)
		invCounter = invCounter.copy().groupby('PART').sum()
		invCounter.reset_index(inplace=True)

		# check to see if scheduling the order will result in shortages.
		# note that because all negative order lines are considered by the inventory counter,
		# there can be lines that produce a negative over what the actual current order shortage is.
		currentOrderLines = unscheduledLines[unscheduledLines['ORDER'] == currentOrder].copy()
		currentShortageCheck = currentOrderLines[['PART','QTYREMAINING']].copy().groupby('PART').sum()
		currentShortageCheck.reset_index(inplace=True)
		invShort = invCounter.copy().append(currentShortageCheck.copy(), sort=False)
		invShort = invShort.groupby('PART').sum()
		invShort.reset_index(inplace=True)
		invShort = invShort[invShort['QTYREMAINING'] < 0].copy()
		# there are shortages listed due to really long floats, this should prevent those shortages causing repetetive loops.
		invShort = invShort[invShort['QTYREMAINING'] < -0.000001].copy()

		# if there are no shortages, then this order can be scheduled right now
		if len(invShort) == 0:
			# schedule current order
			logging.debug('scheduling no shortage')
			logging.debug('scheduling order: ' + str(currentOrder))
			orderPriority, scheduledOrders, dependencies, earliestDateAllowed, unscheduledLines, scheduledLines = sch.schedule_order(currentOrder=currentOrder,
																																 	 orderPriority=orderPriority,
																																 	 laborRequired=laborRequired,
																																 	 laborScheduled=laborUsed,
																																 	 dateListCenter=dateListDict[workCenter],
																																 	 scheduledOrders=scheduledOrders,
																																 	 dependencies=dependencies,
																																 	 earliestDateAllowed=earliestDateAllowed,
																																 	 unscheduledLines=unscheduledLines,
																																 	 scheduledLines=scheduledLines,
																																 	 startDate=dateAttemptStart)
			scheduleSuccess=True
			return (orderPriority,
					scheduledOrders,
					scheduledLines,
					unscheduledLines,
					scheduleSuccess,
					earliestDateAllowed,
					dependencies,
					fakeOrderIter,
					missingLabor,
					missingBOM)
		else:
			# isolate the shortages common to current order lines
			# HEY I THINK invShort is already limiting to order specific lines, so this might be an extra check, not a problem though
			negativeOrderShort = currentShortageCheck[currentShortageCheck['QTYREMAINING'] < 0].copy()
			negativeOrderShort.rename(columns={'QTYREMAINING':'OrderShort'}, inplace=True)
			orderShort = pd.merge(invShort.copy(), negativeOrderShort.copy(), how='left', on='PART')
			orderShort.dropna(inplace=True)
			# if there aren't any inv shortages directly from this order, then it can be scheduled
			if len(orderShort) == 0:
				# schedule current order
				logging.debug('scheduling no applicable shortage')
				logging.debug('scheduling order: ' + str(currentOrder))
				orderPriority, scheduledOrders, dependencies, earliestDateAllowed, unscheduledLines, scheduledLines = sch.schedule_order(currentOrder=currentOrder,
																																	 	 orderPriority=orderPriority,
																																	 	 laborRequired=laborRequired,
																																	 	 laborScheduled=laborUsed,
																																	 	 dateListCenter=dateListDict[workCenter],
																																	 	 scheduledOrders=scheduledOrders,
																																	 	 dependencies=dependencies,
																																	 	 earliestDateAllowed=earliestDateAllowed,
																																	 	 unscheduledLines=unscheduledLines,
																																	 	 scheduledLines=scheduledLines,
																																	 	 startDate=dateAttemptStart)
				scheduleSuccess=True
				return (orderPriority,
						scheduledOrders,
						scheduledLines,
						unscheduledLines,
						scheduleSuccess,
						earliestDateAllowed,
						dependencies,
						fakeOrderIter,
						missingLabor,
						missingBOM)
			else:
				# choose the lesser shortage between inventory counter and order qty for each part
				orderShort['CalcShort'] = np.nan
				orderShort.reset_index(drop=True, inplace=True)
				shawtyCheck = 0
				while shawtyCheck < len(orderShort):
					partInvShort = orderShort['QTYREMAINING'].iat[shawtyCheck]
					partOrderShort = orderShort['OrderShort'].iat[shawtyCheck]
					if partInvShort > partOrderShort:
						orderShort['CalcShort'].iat[shawtyCheck] = partInvShort
					else:
						orderShort['CalcShort'].iat[shawtyCheck] = partOrderShort
					shawtyCheck += 1
				shortage = orderShort[['PART','CalcShort']].copy()

				shortage = pd.merge(shortage.copy(), partDF[['PART','Make/Buy']].copy(), how='left', on='PART')

				# need to resolve all make shortages before you start creating fake POs
				makeShortage = shortage[shortage['Make/Buy'] == 'Make'].copy()
				if len(makeShortage) > 0:
					# the scheduled positive orders before the current attempt date are considered in the shortage already
					# so collect the future positive orders already scheduled to see if they cover the shortage
					# and the unscheduled positive orders (sorted by priority) as well
					futureScheduledLines = scheduledLines[scheduledLines['DATESCHEDULED'] > dateAttemptStart].copy()
					positiveFutureScheduledLines = futureScheduledLines[futureScheduledLines['QTYREMAINING'] > 0].copy()
					positiveUnscheduledLines = unscheduledLines[unscheduledLines['QTYREMAINING'] > 0].copy()
					positiveUnscheduledLines = pd.merge(positiveUnscheduledLines.copy(), orderPriority[['ORDER','Priority']].copy(), how='left', on='ORDER')
					positiveUnscheduledLines.sort_values('Priority', ascending=True, inplace=True)

					for part in makeShortage['PART']:
						# identify the first part, shortage, and relevant order lines
						partShortage = makeShortage[makeShortage['PART'] == part].copy()
						short = partShortage['CalcShort'].iat[0]
						partFutureLines = positiveFutureScheduledLines[positiveFutureScheduledLines['PART'] == part].copy()
						partUnscheduledLines = positiveUnscheduledLines[positiveUnscheduledLines['PART'] == part].copy()
						# loop through until this part's shortage is covered
						while short < 0:
							# start with already scheduled future orders
							if len(partFutureLines) > 0: # set an earliest date limit based on their schedule dates, can't adjust priority because they're scheduled
								logging.debug('checking part future lines: ' + str(part))
								short = short + partFutureLines['QTYREMAINING'].iat[0]
								earliestDateAllowed = sch.attempt_adjust_earliest_start_date(order=currentOrder,
																					  	 	 newDate=partFutureLines['DATESCHEDULED'].iat[0],
																					  	 	 workCenter=workCenter,
																					  	 	 earliestDateList=earliestDateAllowed)
								partFutureLines.drop(partFutureLines.index[0], inplace=True)
							# move on to positive unscheduled orders
							elif len(partUnscheduledLines) > 0: # set a dependency and bump the order priority up
								logging.debug('checking part lines TBD: ' + str(part))
								short = short + partUnscheduledLines['QTYREMAINING'].iat[0]
								dependencies = sch.set_dependency(order=currentOrder,
															  	  dependency=partUnscheduledLines['ORDER'].iat[0],
															  	  dependencyDF=dependencies)
								orderPriority = sch.attempt_adjust_order_priority(adjustOrder=partUnscheduledLines['ORDER'].iat[0],
																			  	  rootOrder=currentOrder,
																			  	  orderPriority=orderPriority)
								partUnscheduledLines.drop(partUnscheduledLines.index[0], inplace=True)
							# then create fake work orders for remaining shortage
							else: # create fake order and place priority one above current order
								OMGPLACEHOLDER, fakeOrderIter = sch.generate_fake_order(fakeOrderIter)
								logging.debug('creating fake order using: ' + str(OMGPLACEHOLDER) + ' for ' + str(part))
								# if OMGPLACEHOLDER == 'P1':
								# 	debug_here()
								laborRef = mfgCenters[mfgCenters['PART'] == part].copy()
								# HEY if the short is multiplied by labor required, it should consider that some BOMs create more than 1 ea of a FG
								if len(laborRef) > 0: # hopefully there's a default BOM reference with a labor estimate
									thisBOM = laborRef['BOM'].iat[0]
									thisCenter = laborRef['MfgCenter'].iat[0]
									if pd.isnull(thisCenter): # if the production center isn't defined then guess pro line
										thisCenter = 'Pro line'
									thisLaborRequ = laborRef['LaborPer'].iat[0]
									if pd.isnull(thisLaborRequ):
										thisLaborRequ = 0
								else:
									missingLabor = sch.add_to_missing_labor(part=part, missingLabor=missingLabor)
									fgBoms = bomDF[bomDF['FG'] == 10].copy()
									fgBoms = fgBoms[fgBoms['PART'] == part].copy()
									if len(fgBoms) > 0:
										# this should be rare if possible
										# it would only happen when there is no record of the "make" part on the mfgCenters list
										# but it still shows up as a finished good on the BOM list as a secondary item to something else
										# though it's likely still impossible.
										thisBOM = fgBoms['BOM'].iat[0]
										# just assign fake center and labor numbers
										thisCenter = 'Pro line'
										thisLaborRequ = 0
									else:
										thisBOM = part + ' NO BOM'
										thisCenter = 'Pro line'
										thisLaborRequ = 0
								# reference the bomDF to create unscheduled order lines
								bomLines = bomDF[bomDF['BOM'] == thisBOM].copy()
								if len(bomLines) > 0: # if the BOM exists, create a set of fake lines
									logging.debug('    BOM exists')
									fgBomLines = bomLines[bomLines['FG'] == 10].copy()
									fgBomLines = fgBomLines[fgBomLines['PART'] == part].copy()
									fgQty = fgBomLines['QTY'].iat[0]
									multiple = abs(short) / fgQty
									bomLines['QTYREMAINING'] = bomLines['QTY'] * multiple
									bomLines['ORDER'] = OMGPLACEHOLDER
									bomLines['ITEM'] = 'Phantom'
									rawGoods = bomLines[bomLines['QTYREMAINING'] <= 0].copy()
									finishGoods = bomLines[bomLines['QTYREMAINING'] > 0].copy()
									rawGoods['ORDERTYPE'] = 'Raw Good'
									finishGoods['ORDERTYPE'] = 'Finished Good'
									bomLines = finishGoods.copy().append(rawGoods.copy(), sort=False)
									bomLines['DATESCHEDULED'] = dateAttemptStart
									bomLines['PARENT'] = currentOrder
									fakeOrderLine = bomLines[['ORDER','ITEM','ORDERTYPE','PART','QTYREMAINING','DATESCHEDULED','PARENT']].copy()
									short = 0
								else: # if BOM doesn't exist, just create a fake finished good line
									logging.debug('    BOM does NOT exist')
									missingBOM = sch.add_to_missing_bom(part=part, missingBOM=missingBOM)
									fgFakePositive = abs(short) # making sure this FG line will be positive, the short value should still be negative
									fakeOrderLine = pd.DataFrame(data={'ORDER': [OMGPLACEHOLDER],
																  	   'ITEM': ['Phantom'],
																  	   'ORDERTYPE': ['Finished Good'],
																  	   'PART': [part],
																  	   'QTYREMAINING': [fgFakePositive],
																  	   'DATESCHEDULED': [dateAttemptStart],
																  	   'PARENT': [currentOrder]})
									multiple = 1
									short = 0

								# add the fake order lines to overall unscheduled lines list
								unscheduledLines = unscheduledLines.copy().append(fakeOrderLine.copy(), sort=False)
								# use the labor required per unit and multiple to retrieve the order's total labor
								thisLabor = thisLaborRequ * multiple
								
								# create fake order priority line
								tempOrderPriority = pd.DataFrame(data={'ORDER': [OMGPLACEHOLDER],
																  	   'DATESCHEDULED': [dateAttemptStart],
																  	   'MfgCenter': [thisCenter],
																  	   'LaborRequired': [thisLabor],
																  	   'Priority': [len(orderPriority)]})
								# add to orderPriority
								orderPriority = orderPriority.copy().append(tempOrderPriority.copy(), sort=False)
								# log it as a dependency
								dependencies = sch.set_dependency(order=currentOrder,
															  	  dependency=OMGPLACEHOLDER,
															  	  dependencyDF=dependencies)
								# move its priority above the current order
								orderPriority = sch.attempt_adjust_order_priority(adjustOrder=OMGPLACEHOLDER,
																		  	  	  rootOrder=currentOrder,
																		  	  	  orderPriority=orderPriority)
					logging.debug('make shortage handled, ' + str(currentOrder))
					scheduleSuccess = True
					return (orderPriority,
							scheduledOrders,
							scheduledLines,
							unscheduledLines,
							scheduleSuccess,
							earliestDateAllowed,
							dependencies,
							fakeOrderIter,
							missingLabor,
							missingBOM)


				else: # section only runs if there are exclusively Buy shortages
					# if currentOrder == '51539/41209':
					# 	debug_here()
					# get a date based on lead time for the earliest these shortages could be filled if purchased now
					shortage.reset_index(drop=True, inplace=True)
					buyShortage = pd.merge(shortage.copy(), leadTimes[['PART','LeadTimes']].copy(), how='left', on='PART')
					buyShortage['LeadTimeDate'] = np.nan
					for line in range(0, len(buyShortage)):
						lead = buyShortage['LeadTimes'].iat[line] + 3 # adding 3 to account for time to place and process order
						dateOptions = referenceDateList[referenceDateList['AvailableLabor'] >= lead].copy()
						leadDate = dateOptions['StartDate'].iat[0]
						rowIndex = buyShortage.index[line]
						buyShortage.at[rowIndex, 'LeadTimeDate'] = leadDate
					# gather a list of all positive orders after the attempted schedule date
					pOrders = scheduledLines[scheduledLines['QTYREMAINING'] > 0].copy()
					pOrders = pOrders[pOrders['DATESCHEDULED'] > dateAttemptStart].copy()
					pOrders.sort_values('DATESCHEDULED', ascending=True, inplace=True)
					for line in range(0, len(buyShortage)):
						# check for positive orders that are also before the earliest a new order would arrive based on lead time			
						rowIndex = buyShortage.index[line]
						part = buyShortage['PART'].iat[line]
						short = buyShortage['CalcShort'].iat[line]
						logging.debug(str(part) + ' is short ' + str(short))
						leadDate = buyShortage['LeadTimeDate'].iat[line]
						relevantOrders = pOrders[pOrders['DATESCHEDULED'] <= leadDate].copy()
						relevantOrders = relevantOrders[relevantOrders['PART'] == part].copy()
						# debug_here()
						if len(relevantOrders) > 0:
							logging.debug('relevant orders:')
							logging.debug(relevantOrders)
							# if the orders cover the buyShortage, use the last lead time necessary to cover it
							if (relevantOrders['QTYREMAINING'].sum() + short) >= 0:
								logging.debug('aaa')
								while short < 0:
									logging.debug('bbb')
									short = short + relevantOrders['QTYREMAINING'].iat[0]
									relevantDate = relevantOrders['DATESCHEDULED'].iat[0]
									relevantOrders = relevantOrders.iloc[1:] # dropping the top row by location
									# relevantOrders.drop(relevantOrders.index[0], inplace=True) # this was dropping extra rows due to duplicate indexes
								buyShortage.at[rowIndex, 'CalcShort'] = short
								buyShortage.at[rowIndex, 'LeadTimeDate'] = relevantDate
								logging.debug('ccc ' + str(short) + ' date: ' + str(relevantDate))
							# if the orders don't cover the shortage, then adjust the shortage to use all of them
							# but don't change the lead time, since a purchase has to be made still
							else:
								logging.debug('-- no relevant orders --')
								buyShortage.at[rowIndex, 'CalcShort'] = short + relevantOrders['QTYREMAINING'].sum()
					# grab the longest lead time
					buyShortage.sort_values('LeadTimeDate', ascending=False, inplace=True)
					longestLeadDate = buyShortage['LeadTimeDate'].iat[0]
					# if the longest lead is after 
					if longestLeadDate > dateAttemptStart:
						logging.debug('-- lead date after attempted start date')
						earliestDateAllowed = sch.attempt_adjust_earliest_start_date(order=currentOrder,
														   						 	 newDate=longestLeadDate,
														   						 	 workCenter=workCenter,
														   						 	 earliestDateList=earliestDateAllowed)
					else:
						logging.debug('-- lead date in range; making fake order lines')
						fakePOLines = buyShortage[buyShortage['CalcShort'] < 0].copy()
						fakePOLines['QTYREMAINING'] = fakePOLines['CalcShort'].copy() * (-1)
						fakePOLines['ITEM'] = 'Phantom'
						fakePOLines['ORDERTYPE'] = 'Purchase'
						fakePOLines['DATESCHEDULED'] = longestLeadDate
						fakePOLines['PARENT'] = currentOrder
						fakePOLines['ORDER'] = np.nan
						fakePOLines['ORDER'] = fakePOLines['ORDER'].astype('str')
						for poLine in range(0, len(fakePOLines)):
							OMGPLACEHOLDER, fakeOrderIter = sch.generate_fake_order(fakeOrderIter)
							# debug_here()
							fakePOLines.at[fakePOLines.index[poLine], 'ORDER'] = OMGPLACEHOLDER
						fakePOLines = fakePOLines[['ORDER','ITEM','ORDERTYPE','PART','QTYREMAINING','DATESCHEDULED','PARENT']].copy()
						scheduledLines = scheduledLines.copy().append(fakePOLines.copy(), sort=False)

						# schedule current order
						logging.debug('scheduling order: ' + str(currentOrder))
						print('scheduling ' + str(currentOrder))
						print(currentOrder)
						orderPriority, scheduledOrders, dependencies, earliestDateAllowed, unscheduledLines, scheduledLines = sch.schedule_order(currentOrder=currentOrder,
																																			 	 orderPriority=orderPriority,
																																			 	 laborRequired=laborRequired,
																																			 	 laborScheduled=laborUsed,
																																			 	 dateListCenter=dateListDict[workCenter],
																																			 	 scheduledOrders=scheduledOrders,
																																			 	 dependencies=dependencies,
																																			 	 earliestDateAllowed=earliestDateAllowed,
																																			 	 unscheduledLines=unscheduledLines,
																																			 	 scheduledLines=scheduledLines,
																																			 	 startDate=dateAttemptStart)
					logging.debug('buy shortage handled, ' + str(currentOrder))
					scheduleSuccess = True
					return (orderPriority,
							scheduledOrders,
							scheduledLines,
							unscheduledLines,
							scheduleSuccess,
							earliestDateAllowed,
							dependencies,
							fakeOrderIter,
							missingLabor,
							missingBOM)
	return (orderPriority,
			scheduledOrders,
			scheduledLines,
			unscheduledLines,
			scheduleSuccess,
			earliestDateAllowed,
			dependencies,
			fakeOrderIter,
			missingLabor,
			missingBOM)



# beginning of loop

print('entering loop')

# this loop will need to watch for a point when no orders can be scheduled due to lead times.
# make items discover their dependencies before finding earliest schedule dates
# so all of the dependencies will be worked out before this lead time issue comes up.

scheduledLines = poDF.copy() # the POs are already scheduled, so list them in scheduled orders
unscheduledLines = soDF.copy().append(moDF.copy(), sort=False) # all SO and MO lines are unscheduled to start and they are in orderPriority as well

# if the last loop didn't end up in a schedule success, then add in
# an order called labor gap.  It will bump the attempted schedule date
# for the first order in to range of that orders earliest allowed schedule date.
scheduleSuccess = True # this just makes the first loop run without entering the conditional clause.
while len(orderPriority) > 0:
	orderPriority.reset_index(drop=True, inplace=True) # might need to do this to make sure rows nums and indexes match for ease
	# debug_here()
	if scheduleSuccess == False:
		print('000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000')
		print('should be making a gap order')
		logging.debug('scheduleSuccess is False')
		# check only for orders that don't have dependencies listed
		indyOrders = orderPriority.copy().append(dependencies.copy(), sort=False)
		indyOrders.drop_duplicates('ORDER', keep=False, inplace=True)
		if len(indyOrders) > 0: # I think this should always be true at this point, but just in case ...
			logging.debug('creating gap order')
			# find the earliest start date possible for orders without dependencies
			indyOrders = pd.merge(indyOrders.copy(), earliestDateAllowed[['ORDER','startDateLimit']].copy(), how='left', on='ORDER')
			indyOrders.sort_values('startDateLimit', ascending=True, inplace=True)
			limitOrder = indyOrders['ORDER'].iat[0]
			# calculate expected labor gap
			workCenter = indyOrders['MfgCenter'].iat[0]
			gapDate = indyOrders['startDateLimit'].iat[0]
			gapCenter = indyOrders['MfgCenter'].iat[0]
			availableLabor = dateListDict[gapCenter].copy()
			availableLabor = availableLabor[availableLabor['StartDate'] >= gapDate].copy()
			limitLabor = availableLabor['AvailableLabor'].iat[0]
			laborUsed = 0
			prevSchedLabor = scheduledOrders[scheduledOrders['MfgCenter'] == workCenter].copy()
			if len(prevSchedLabor) > 0:
				laborUsed = prevSchedLabor['LaborRequired'].sum()
			# save the start date for the gap
			availableLabor = dateListDict[gapCenter].copy()
			availableLabor = availableLabor[availableLabor['AvailableLabor'] > laborUsed].copy()
			gapStart = availableLabor['StartDate'].iat[0]
			# add labor gap as a scheduled order for its production area
			gapLabor = limitLabor - laborUsed
			gapOrder, fakeOrderIter = sch.generate_fake_order(fakeOrderIter)
			gapOrder = gapOrder + 'gap'
			gapLine = pd.DataFrame(data={'ORDER': [gapOrder],
										 'DATESCHEDULED': [gapDate],
										 'MfgCenter': [gapCenter],
										 'LaborRequired': [gapLabor],
										 'Priority': [len(orderPriority)],
										 'STARTDATE': [gapStart]})
			scheduledOrders = scheduledOrders.copy().append(gapLine.copy(), sort=False)
			print(gapOrder)
		else: # this would only happen if there are dependencies creating a loop with each other (A need B, B also needs A)
			# find the earliest start date possible for all remaining orders
			priorityOrderCheck = pd.merge(orderPriority.copy(), earliestDateAllowed[['ORDER','startDateLimit']].copy(), how='left', on='ORDER')
			priorityOrderCheck.sort_values('startDateLimit', ascending=True, inplace=True)
			scheduleOrder = priorityOrderCheck['ORDER'].iat[0]
			### calculate expected labor gap for first orders production area
			### add labor gap as a scheduled order for its production area
			### sch.schedule_order()
			### temporarily causing error because I don't expect this to happen:
			print('possible eternal loop')
			# print('OOOOOOOOOOOOOOOOOHHHHHHHHHHHHNOOOOOOOOOOOOOOOOOOOOOOOOOOO')
			priorityOrderCheck['fakeColumnforError'].iat[0] # this should error out, I want to see when this happens.
	# run the next order schedule attempt, if the previous run's success was false, then a labor gap filler should make this run successful.
	orderPriority, scheduledOrders, scheduledLines, unscheduledLines, scheduleSuccess, earliestDateAllowed, dependencies, fakeOrderIter, missingLabor, missingBOM = order_schedule_attempt(orderPriority=orderPriority,
																																													   	   scheduledOrders=scheduledOrders,
																																													   	   scheduledLines=scheduledLines,
																																													   	   unscheduledLines=unscheduledLines,
																																													   	   earliestDateAllowed=earliestDateAllowed,
																																													   	   dependencies=dependencies,
																																													   	   dateListDict=dateListDict,
																																													   	   invDF=invDF,
																																													   	   partDF=partDF,
																																													   	   fakeOrderIter=fakeOrderIter,
																																													   	   mfgCenters=mfgCenters,
																																													   	   bomDF=bomDF,
																																													   	   leadTimes=leadTimes,
																																													   	   referenceDateList=referenceDateList,
																																													   	   missingLabor=missingLabor,
																																													   	   missingBOM=missingBOM)


inventoryCounter = sch.add_inv_counter(inputTimeline=scheduledLines.copy(), backdate='1999-12-31 00:00:00', invdf=invDF.copy())

# debug_here()

# startingInv = invDF.rename(columns={'INV':'QTYREMAINING'}).copy()
# startingInv['DATESCHEDULED'] = todayTimestamp
# startingInv['ITEM'] = 'Inventory'
# startingInv['ORDER'] = 'Inventory'
# startingInv['ORDERTYPE'] = 'Inventory'
# startingInv['PARENT'] = 'Inventory'

# inventoryCounter = scheduledLines.copy().append(startingInv.copy(), sort=True)
# inventoryCounter.reset_index(drop=True, inplace=True)
# inventoryCounter.sort_values(by=['PART','DATESCHEDULED'], ascending=[True,True], inplace=True)
# inventoryCounter


print('saving results')
# save a copy of the schedule to excel
writer = pd.ExcelWriter(finalSchedFilename)
orderPriority.to_excel(writer, 'orderPriority')
scheduledOrders.to_excel(writer, 'scheduledOrders')
scheduledLines.to_excel(writer, 'scheduledLines')
unscheduledLines.to_excel(writer, 'unscheduledLines')
earliestDateAllowed.to_excel(writer, 'earliestDateAllowed')
dependencies.to_excel(writer, 'dependencies')
leadTimes.to_excel(writer, 'leadTimes')
inventoryCounter.to_excel(writer, 'inventoryCounter')
writer.save()

print('noting missing data')
missingLabor.drop_duplicates('PART', keep='first', inplace=True)
missingBOM.drop_duplicates('PART', keep='first', inplace=True)
missingLabor.sort_values(by='PART', inplace=True)
missingBOM.sort_values(by='PART', inplace=True)

writer = pd.ExcelWriter(missingFilename)
missingLabor.to_excel(writer, 'missingLabor')
missingBOM.to_excel(writer, 'missingBOM')
writer.save()

print('analyzing dependencies')
dp.dependencies()

print('end of the lines')


"""

Consider error handling for missing BOMs and negative inventory (shouldn't happen when orders are scheduled).
Could avoid complicated BOMs missing tracking by creating a make parts missing BOMs list at the start.
At the end, just reference all parts fake ordered from that list for the total.

"""
