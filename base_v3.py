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
invFilename = os.path.join(dataPath, 'INVs.xlsx')
soFilename = os.path.join(dataPath, 'SOs.xlsx')
poFilename = os.path.join(dataPath, 'POs.xlsx')
partFilename = os.path.join(dataPath, 'Parts.xlsx')
descFilename = os.path.join(dataPath, 'Descs.xlsx')
bomFilename = os.path.join(dataPath, 'BOMs.xlsx')
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


### GET DATA ###

# save mfgCenters as df, includes MFG Center assignments and Setup/labor time estimates
mfgCenters = pd.read_excel(mfgCentersFilename, header=0)

# save current Manufacture Orders
moDF = pd.read_excel(moFilename, header=0)

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

# save current BOMs
bomDF = pd.read_excel(bomFilename, header=0)

# save current part descriptions
descDF = pd.read_excel(descFilename, header=0)

# save current inventory
invDF = pd.read_excel(invFilename, header=0)

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

# save current parts list - doubt this is needed, maybe combine with something else like desc and avgcost
partDF = pd.read_excel(partFilename, header=0)

# save current Sales Orders
soDF = pd.read_excel(soFilename, header=0)

# save current Purchase Orders
poDF = pd.read_excel(poFilename, header=0)


### Sort Orders by Priority ###

# need a list of orders and way to prioritize them, can be handled a few ways.
# for now we'll just pretend that the SOs and MOs are coming in order of priority already.

soPriority = soDF.drop_duplicates('ORDER', keep='first').copy()
moPriority = moDF.drop_duplicates('ORDER', keep='first').copy()
orderPriority = soPriority.copy().append(moDF.copy())

# create a dataFrame for tracking earliest start date allowed limitations
earliestDateAllowed = pd.DataFrame(columns=['ORDER','startDateLimit'])

# create a dataFrame for tracking order dependency, aka any orders needing to be scheduled before this one
dependencies = pd.DataFrame(columns=['ORDER','dependency'])




# this function is for setting new earliest start dates for orders.
# it will not set a date for a specific order if it is already set for a later date.
def attempt_adjust_earliest_start_date(order, newDate, earliestDateList):
	dateListCheck = earliestDateList[earliestDateList['ORDER'] == order].copy()
	if len(dateListCheck) > 0: # if it has no rows, then the order just needs to be appended
		if dateListCheck['startDateLimit'].iat(0) < newDate: # if not then it will keep the later date
			rowIndex = earliestDateList.loc[earliestDateList['ORDER'] == order].index[0]
			earliestDateList.at[rowIndex, 'startDateLimit'] = newDate
	else: # adds a fresh line with the order and its date limit
		tempDateDF = pd.DataFrame([order, newDate], columns=['ORDER','startDateLimit'])
		earliestDateList = earliestDateList.copy().append(tempDateDF.copy())
	return earliestDateList.copy()

Save Starting Inventory for reference

# beginning of loop


# this loop will need to watch for a point when no orders can be scheduled due to lead times.
# make items discover their dependencies before finding earliest schedule dates
# so all of the dependencies will be worked out before this lead time issue comes up.

scheduledOrders = poDF.copy() # the POs are already scheduled, so list them in scheduled orders
unScheduledOrders = soDF.copy().append(moDF.copy()) # all SOs and MOs are unscheduled to start and they are in orderPriority as well

# if the last loop didn't end up in a schedule success, then add in
# an order called labor gap.  It will bump the attempted schedule date
# for the first order in to range of that orders earliest allowed schedule date.
scheduleSuccess = True # this just makes the first loop run without entering the conditional clause.
while len(orderPriority) > 0:
	orderPriority.reset_index(drop=True, inplace=True) # might need to do this to make sure rows nums and indexes match for ease
	if scheduleSuccess == False:
		# check only for orders that don't have dependencies listed
		indyOrders = orderPriority.copy().append(dependencies.copy())
		indyOrders.drop_duplicates('ORDER', keep=False, inplace=True)
		if len(indyOrders) > 0: # I think this should always be true at this point, but just in case ...
			# find the earliest start date possible for orders without dependencies
			indyOrders = pd.merge(indyOrders.copy(), earliestDateAllowed.copy(), how='left', on='ORDER')
			indyOrders.sort_values('startDateLimit', ascending=True, inplace=True)
			scheduleOrder = indyOrders['ORDER'].iat[0]
			### calculate expected labor gap
			### add labor gap as a scheduled order for its production area
		else: # this would only happen if there are dependencies creating a loop with each other (A need B, B also needs A)
			# find the earliest start date possible for all remaining orders
			priorityOrderCheck = pd.merge(priorityOrderCheck.copy(), earliestDateAllowed.copy(), how='left', on='ORDER')
			priorityOrderCheck.sort_values('startDateLimit', ascending=True, inplace=True)
			scheduleOrder = priorityOrderCheck['ORDER'].iat[0]
			### calculate expected labor gap for first orders production area
			### add labor gap as a scheduled order for its production area
	# run the next order schedule attempt, if the previous run's success was false, then a labor gap filler should make this run successful.
	orderPriority, scheduledOrders, unScheduledOrders, scheduleSuccess, earliestDateAllowed, dependencies = function_below(orderPriority,
																											 			   scheduledOrders,
																											 			   unScheduledOrders,
																											 			   earliestDateAllowed,
																											 			   dependencies,
																											 			   invDF)


# beginning of function_below()
scheduleSuccess = False
x = 0
while x < len(orderPriority):
	orderPriority.reset_index(drop=True, inplace=True) # might need to do this to make sure rows nums and indexes match for ease


	# Check if starting inventory plus all scheduled orders results in any negatives:
	# 	error out if true
	currentOrderSum = scheduledOrders[['PART','QTYREMAINING']].copy().groupby('PART').sum()
	currentOrderSum.reset_index(inplace=True)
	currentOrderSum.rename(columns={'QTYREMAINING':'INV'}, inplace=True)
	currentInvSum = invDF.copy().append(currentOrderSum.copy())
	currentInvSum.groupby('PART').sum()
	negativeInv = currentInvSum[currentInvSum['INV'] < 0]
	if len(negativeInv) > 0: # if any inventory lines are negative, this will be true
		print(negativeInv)
		True = False # I think this will throw an error


	?Check first pri order for earliest available schedule time according to labor group (probably Shipping on first loop)


	
	if the start date is before earliest allowed start date on earliest date list:
		move on to next priority order
		x+=1
	if there are any unscheduled dependencies on dependency list or any dependencies scheduled after current attempted date:
		move on to next priority order
		x+=1
	Make an Inventory Counter:
		Add all POs fulfilled by attempted start date
		Add all positive order lines already scheduled by attempted start date
		Subtract all negative order lines already scheduled, including any scheduled after attempted start date

	if first pri order makes any part negative based on Inventory Counter:
		shortage = parts and resulting negative quantities
		# need to resolve all make shortages before you start creating fake POs
		if there are shortages for make parts:
			# will need to add a section searching for existing orders here
			# just find where the orders cover the shortage then move their priorities up and set dependencies
			# then fake for whatever's left.
			# try this out:
			for each make shortage:
				mOrders = work orders where scheduled positive arrival in order of priority
				if len(mOrders) > 0:
					while shortage < 0:
						add first work order in mOrders to shortage
						place first work order priority just above current order in priority list
				if shortage < 0:
					create fake work order for shortage qty using BOM
					place fake work order priority just above current order in priority list
					add fake order to dependency list for current order
			scheduleSuccess = True
			return (orderPriority, scheduledOrders, unScheduledOrders, scheduleSuccess, earliestDateAllowed, dependencies)
		# buy shortage time
		else:
			Lead time dates = earliest arrival based on lead time (if bought tomorrow) for all buy shortages
			for each buy shortage:
				pOrders = purchase orders where scheduled positive arrival date is after current schedule attempt date and before Lead time date
				if len(pOrders) > 0:
					if (sum of pOrders + shortage) is >= 0: # if the POs will cover the shortage
						while shortage < 0:
							shortage = add first pOrders qty to shortage
							set Lead time dates of part to first pOrders schedule date
							delete first line from pOrders
					else:
						shortage = shortage + sum of pOrders # shortage will still be negative and lead time is unaffected
			Longest lead time date = latest of the arrival dates in Lead time dates
			if Longest lead time date is after current attempt:
				attempt_adjust_earliest_start_date(order, Longest lead time date, earliest date list)
			else:
				create fake POs for all negative shortages and set their fulfillment dates equal to Longest lead time date
				schedule current order at current attempted date
				remove current order from priority list
				remove all dependencies listed for this order
			scheduleSuccess = True
			return (orderPriority, scheduledOrders, unScheduledOrders, scheduleSuccess, earliestDateAllowed, dependencies)

	else:
		schedule first pri order
		remove first pri order from priority list
		remove all dependencies listed for this order
		scheduleSuccess = True
		return (orderPriority, scheduledOrders, unScheduledOrders, scheduleSuccess, earliestDateAllowed, dependencies)
return (orderPriority, scheduledOrders, unScheduledOrders, scheduleSuccess, earliestDateAllowed, dependencies)








"""
SO priority comes from Fishbowl?
MO priority comes from same.

Scheduling SO fulfillment requires some awareness of shipping labor available/required.
Set a value of labor required per line (either stored on part or product).
Use that to create a labor required total for each SO.
Then schedule SOs the same way as MOs but to Shipping's available labor.

Also, whenever an order is scheduled, add it to a list.
This will allow you to check what order it ended up using.

Consider error handling for missing BOMs and negative inventory (shouldn't happen when orders are scheduled).
Could avoid complicated BOMs missing tracking by creating a make parts missing BOMs list at the start.
At the end, just reference all parts fake ordered from that list for the total.

If you're trying to figure out how many loops it's going through,
use print(loopnumber, end='').  Should print on one line to make
it a bit more readable.

When you hit a necessary labor gap, add an order called labor gap.  At the end, you'll be
able to calculate how much labor gap was spent in each area.


"""
