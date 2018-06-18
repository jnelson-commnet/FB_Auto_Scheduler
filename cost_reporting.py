import pandas as pa
import os
import numpy as np

# save current working directory as homey
homey = os.path.abspath(os.path.dirname(__file__))
# homey = os.getcwd() # works in jupyter notebook

# set directory paths
dataPath = os.path.join(homey, 'data')

# set paths to excel files
partFilename = os.path.join(dataPath, 'Parts.xlsx')
invFilename = os.path.join(dataPath, 'INVs.xlsx')
finalSchedFilename = os.path.join(homey, 'finalSchedule.xlsx')

print('retrieving data')

# save current inventory
invDF = pd.read_excel(invFilename, header=0)
invDF['INV'] = invDF['INV'].round(2) # just getting the floats out.
# save current parts list
partDF = pd.read_excel(partFilename, header=0)
# get transaction list from auto_scheduler
transact = pd.read_excel(finalSchedFilename, sheet_name='scheduledLines', header=0)



inv = pd.merge(partDF.copy(), invDF.copy(), how='left', on='PART')
inv['INV'].fillna(0, inplace=True)
inv['ORDERTYPE'] = 'Starting Inventory'
inv['ORDER'] = 'StartingInv'
inv['ITEM'] = 0



for part in transact.PART:
	tempdf = inv where inv.part == part
	format tempdf to match transact
	tempdf.append(transact where transact.PART == part)
	# now you have starting inventory at the top
	# can get ending inventory (stranded) anytime now by summing total transactions against starting inventory
	create relation list for this part's transactions

input() a part and order (like a PO or starting inventory)
analyze for:
	- stranded inventory (qty and cost of ending inventory)
	- direct backlog contributions (qty and cost directly used on an SO)
	- builds used on (then check those builds for ratio of: - stranded inventory (equates as speculative for original part)
												   			- backlog contributions (is considered backlog contribution for original part)
												   			- speculative builds (recursive until all are checked))
	

	






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