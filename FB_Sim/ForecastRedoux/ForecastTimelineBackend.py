__author__ = 'Chris'

import pandas as pd
import ForecastBOMExploder as bom
import datetime as dt
import ForecastSettings as fs


"""This creates the BOM tier part lists."""
"""Remake of other function, drops runtime from 12 mins to under a second.  Hope it doesn't have bugs."""
def create_bom_tiers_v2(bomsdf, partsdf):
    partlist = bomsdf.drop_duplicates('PART').copy()  # list of all part numbers on active BOMs
    partstemp = partsdf.PART.drop_duplicates().copy()
    partstemp = partstemp.copy().append(partlist['PART'].copy())
    buyparts = partstemp.drop_duplicates(keep=False).copy()  # all parts that don't exist on an active BOM

    tierdict = {}
    current_tier_index = 1
    current_tier_parts = []

    print('section 1')
    ''' This section isolates the parts that exist as FG on BOMs but not as Raw Goods. '''
    ''' This will create the first tier of parts based on its result.                  '''
    fglist = bomsdf[bomsdf.FG == 10].copy()
    uniqueFG = fglist.drop_duplicates('PART').copy()
    rglist = bomsdf[bomsdf.FG == 20].copy()
    uniqueFG = uniqueFG.copy().append(rglist.copy())
    uniqueFG.drop_duplicates('PART', keep=False, inplace=True)
    uniqueFG = uniqueFG[uniqueFG.FG == 10].copy()

    current_tier_parts = uniqueFG['PART'].tolist().copy()  # Convert the list of FG to a list
    tierdict[current_tier_index] = current_tier_parts  # and add it as the first tier to the dict

    tierTracker = pd.DataFrame()  # declaring the DF that holds the part number tiers
    tierTracker['PART'] = uniqueFG.PART.copy()  # add the list of BOM parts that are only FG as the first tier

    partlist = rglist.drop_duplicates('PART').copy()  # The parts list is just all Raw Goods on active BOMs now

    print('section 2')
    # current_tier_index = 2 ### This note is kinda deceiving, it currently equals 1 but will be up to 2 before saving again.

    while len(partlist) > 0:

        tierTracker['TIER'] = tierTracker['PART'].copy()
        newfglist = pd.merge(fglist.copy(), tierTracker.copy(), how='left', on='PART') ### This might need to be limited to part of tierTracker
        newfglist = newfglist[newfglist['TIER'].isnull()].copy()
        newfglist['TIER'] = 1

        rawChecker = pd.merge(bomsdf.copy(), newfglist[['BOM','TIER']].copy(), how='left', on='BOM')
        rawChecker.dropna(subset=['TIER'], inplace=True)
        rawChecker = rawChecker[rawChecker['FG'] == 20].copy()
        rawChecker.drop_duplicates('PART', inplace=True)

        partlist = pd.merge(partlist.copy(), rawChecker[['PART','TIER']].copy(), how='left', on='PART')

        nextTier = partlist[partlist['TIER'].isnull()].copy()
        current_tier_parts = nextTier['PART'].tolist().copy()
        current_tier_index += 1
        tierdict[current_tier_index] = current_tier_parts
        print('tier', current_tier_index, 'created')

        if len(current_tier_parts) == 0:  # If the tier list just saved was actually empty
            tierdict[current_tier_index] = partlist['PART'].tolist().copy()  # Then save whatever is left on the partlist
            break  # and move on to the next step

        tierTracker = tierTracker.copy().append(nextTier[['PART','TIER']].copy())

        partlist.dropna(subset=['TIER'], inplace=True)
        partlist.drop('TIER', axis='columns', inplace=True)

    print('section 3')
    current_tier_index += 1  # Increase the tier index one last time
    tierdict[current_tier_index] = buyparts.tolist().copy()  # and add all the parts that don't exist on any active BOM as the final tier
    
    return tierdict  # return the dict


"""Creating proper parents for MOs"""
def create_mo_parents(orgdf):
    molist = orgdf.MOID.unique()
    for each in molist:
        tempdf = orgdf.ix[orgdf['MOID'] == each].copy()
        tempfindf = tempdf.ix[tempdf['ORDERTYPE'] == 'Finished Good'].copy()
        temprawdf = tempdf.ix[tempdf['ORDERTYPE'] == 'Raw Good'].copy()
        for index, row in tempdf.iterrows():
            tempfinpart = tempfindf.ix[tempfindf['ORDER'] == row['ORDER']].copy()
            if not tempfinpart.empty:
                tempfinpart.reset_index(drop=True, inplace=True)
                temprawpart = temprawdf.ix[temprawdf['PART'] == tempfinpart.ix[0, 'PART']].copy()
                if not temprawpart.empty:
                    tempparent = temprawdf.ix[temprawdf['PART'] == tempfinpart.ix[0, 'PART']]
                    tempparent.reset_index(drop=True, inplace=True)
                    tempparent = tempparent.loc[0, 'ORDER']
                    testparent = tempfindf.ix[tempfindf['ORDER'] == tempparent].copy()
                    newparent = testparent.reset_index(drop=True, inplace=False)
                    testrawparent = temprawdf[temprawdf['PART'] == newparent.loc[0, 'PART']].copy()
                    if testrawparent.empty:
                        orgdf.loc[index, 'PARENT'] = tempparent
                    else:
                        parentindex = testparent.index.tolist()
                        tempnewparent = orgdf.loc[parentindex[0], 'PARENT']
                        orgdf.loc[index, 'PARENT'] = tempnewparent
    orgdf = orgdf.drop('MOID', 1)
    return orgdf

"""Takes orders and inv and finds the first shortages"""  ### No longer used in normal runs of Forecast.  Once add_order and remove_order are updated, this will be deprecated.
def find_next_shortage_redoux(invdf, postordersdf):
    postordersdf.reset_index(drop=True, inplace=True)
    partslist = postordersdf.PART.unique()
    shortagedf = pd.DataFrame()
    column_headers = ['ORDER', 'ITEM', 'ORDERTYPE', 'PART', 'QTYREMAINING', 'DATESCHEDULED', 'PARENT', 'Make/Buy']
    preordersdf = pd.DataFrame(columns=column_headers)
    for each in partslist:
        tempordersdf = postordersdf.ix[postordersdf['PART'] == each].copy()
        tempordersdf['DATESCHEDULED'] = pd.to_datetime(tempordersdf['DATESCHEDULED'])
        tempordersdf = tempordersdf.sort_values(by=['DATESCHEDULED', 'QTYREMAINING', 'ORDER'], ascending=[True, False, True])
        currentinv = invdf.loc[invdf['PART'] == each]
        if currentinv.empty:
            workinginv = 0
            tempinvdf = pd.DataFrame({'PART': [each], 'INV': [0]})
            invdf = invdf.append(tempinvdf)
        else:
            currentinv.reset_index(drop=True, inplace=True)
            workinginv = currentinv.at[0,'INV']
        for index, row in tempordersdf.iterrows():
            if (workinginv <= 0 and row['QTYREMAINING'] < 0): #This is the heart of the loop
                shortagedf = shortagedf.append(row)
                # tempordersdf.ix[index]['PriorInv'] = workinginv
                preordersdf = preordersdf.append(tempordersdf.ix[index])
                workinginv = workinginv + row['QTYREMAINING']
                postordersdf = postordersdf.drop(labels=index)
                break
            else:
                # tempordersdf.ix[index]['PriorInv'] = workinginv
                preordersdf = preordersdf.append(tempordersdf.ix[index])
                workinginv = workinginv + row['QTYREMAINING']
                postordersdf = postordersdf.drop(labels=index)
                if (workinginv < 0 and row['QTYREMAINING'] < 0):
                    row['QTYREMAINING'] = workinginv
                    shortagedf = shortagedf.append(row)
                    break
        invdf.ix[(invdf['PART'] == each),'INV'] = workinginv
    return [shortagedf, postordersdf, preordersdf, invdf]

"""Find the next shortage within the tier."""
def find_next_shortage_redux(invdf, postordersdf, tierlist):
    # print('post orders in -------')
    # print(' ')
    # if len(postordersdf) != 0:
    #     print(postordersdf)
    postordersdf.reset_index(drop=True, inplace=True)
    partslist = []
    ''' I'm not sure that these next few lines are necessary.  The postordersdf is already coming in paired down to current tier parts.
        If it's needed, you could change it to partslist = postorders.PART.unique() and not pass the tierlist at all '''
    for each in postordersdf.PART.unique():  # For each unique part found on the orderslist
        if each in tierlist:  # if it's in the current list of parts to run
            partslist.append(each)  # then add it to partslist

    shortagedf = pd.DataFrame()
    column_headers = ['ORDER', 'ITEM', 'ORDERTYPE', 'PART', 'QTYREMAINING', 'DATESCHEDULED', 'PARENT', 'Make/Buy']
    preordersdf = pd.DataFrame(columns=column_headers)

    for each in partslist:  # for every part (that exists in the orders sheet)
        tempordersdf = postordersdf.ix[postordersdf['PART'] == each].copy()  # Make a temporary df of all orders involving that part
        tempordersdf['DATESCHEDULED'] = pd.to_datetime(tempordersdf['DATESCHEDULED'])  # make sure the dates are all in datetime format
        tempordersdf = tempordersdf.sort_values(by=['DATESCHEDULED', 'QTYREMAINING', 'ORDER'], ascending=[True, False, True])  # Sort the temporary df of this part's orders
        ''' Sort by oldest to newest first.  Secondarily, highest quantity change to lowest (so the positive PO's will be counted before the negative SO's).
            Then sort by order, which doesn't seem very important, but why not. '''
        currentinv = invdf.loc[invdf['PART'] == each]  # Grab the current part's inventory

        '''
        For this next part, if there's no record of the current part in the inventory df, the workinginv needs to be set to 0.
            And the a line is added to the inventory df to include that inventory of 0.
        If there is a record of inventory to pull, then use that to set workinginv.
        '''
        if currentinv.empty:
            workinginv = 0
            tempinvdf = pd.DataFrame({'PART': [each], 'INV': [0]})
            invdf = invdf.append(tempinvdf)
        else:
            currentinv.reset_index(drop=True, inplace=True)
            workinginv = currentinv.at[0,'INV']

        '''
        Loop through each of the orders for this part.  Each loop checks inventory and the order and decides
        where to save the order.  It will update the inventory and break once it hits a point where there's no inv
        and it's on an order that would cause a drop in inventory (like a SO).
        '''
        for index, row in tempordersdf.iterrows():
            '''

            '''
            # print(row)
            if (workinginv <= 0 and row['QTYREMAINING'] < 0): #This is the heart of the loop.  If out of inv and the order reducing it further:
                # print('section A')
                shortagedf = shortagedf.copy().append(row)  # save the order to shortages
                # tempordersdf.ix[index]['PriorInv'] = workinginv # what is this?
                preordersdf = preordersdf.append(tempordersdf.ix[index]) # save the order to preorders
                workinginv = workinginv + row['QTYREMAINING']  # adjust inv based on the order
                postordersdf = postordersdf.drop(labels=index)  # drop the order from postorders
                break  # exit the loop of this part
            else:  # If either the inv or the order are positive
                # print('section B')
                # tempordersdf.ix[index]['PriorInv'] = workinginv # what is this?
                preordersdf = preordersdf.append(tempordersdf.ix[index])  # save order to preorders
                workinginv = workinginv + row['QTYREMAINING']  # adjust inv based on the order
                postordersdf = postordersdf.drop(labels=index)  # drop the order from postorders
                if (workinginv < 0 and row['QTYREMAINING'] < 0):  # if inv is now negative and the order row was also negative
                    # print('section C')
                    row['QTYREMAINING'] = workinginv  # then make the order qty equal to inventory since that is how much this is short
                    shortagedf = shortagedf.append(row)  # and add it to shortages
                    break  # breaker out of this part's loop
        # print('-----------')
        # print(invdf[invdf['PART'] == each])
        # print(workinginv)
        invdf.ix[(invdf['PART'] == each),'INV'] = workinginv  # set the part's inventory to the result of this round of order checks.
        # print(invdf[invdf['PART'] == each])
    # print(' ')
    # print('post orders out ----------')
    # print(' ')
    # if len(postordersdf) != 0:
    #     print(postordersdf)
    # print(' ')
    return [shortagedf.copy(), postordersdf.copy(), preordersdf.copy(), invdf.copy()]

"""Makes new orders to put back into timeline."""
def make_new_orders(shortordersdf, bomsdf, missingbomlist, manybomlist):
    # print(shortordersdf)
    # save column headers for use later
    column_headers = ['ORDER', 'ITEM', 'ORDERTYPE', 'PART', 'QTYREMAINING', 'DATESCHEDULED', 'PARENT', 'Make/Buy']
    # create an empty dataFrame with the column headers .... used to return the fresh orders at end of function
    newordersdf = pd.DataFrame(columns=column_headers)

    # loop through the list of order shortages given
    for index, row in shortordersdf.iterrows():
        # print('row')
        # print(row)
        # save the fake order number for the phantom or imaginary order
        if row['ITEM'] == 'Imaginary':
            order = fs.Index().show_fake_index()
        else:
            order = fs.Index().show_index()

        # save the item title for phantom or imaginary order
        if row['ITEM'] == 'Imaginary':
            item = 'Imaginary'
        else:
            item = 'Phantom'

        # if the shortage is a "Make" part then it would be the Finished Good for the fake order
        #   use the order_exploder() function to make fake orders for all the raw goods as well
        # if the shortage is not a "Make" part, then the order type would be Purchase
        if row['Make/Buy'] == 'Make':
            ordertype = 'Finished Good'
            bomdf = bom.order_exploder(bomsdf, row, order, missingbomlist, manybomlist)
            newordersdf = newordersdf.copy().append(bomdf.copy())
        else:
            ordertype = 'Purchase'

        # save part number
        part = row['PART']
        # save quantity (the incoming quantity should be negative since it is a shortage.  This switches it to positive for the fake order.)
        qty = (row['QTYREMAINING'] * -1)
        # save the date as one day before it is scheduled as short.   ### If you change the days to a variable, can do more lead times.
        date = pd.to_datetime(row['DATESCHEDULED']) - dt.timedelta(days=1) #This is a lead time
        date = date.date() # not sure what this does, maybe just returns it as a datetime object
        # save the parent order
        parent = row['ORDER']
        # save its make/buy type
        mb = row['Make/Buy']
        tempdatalist = [order, item, ordertype, part, qty, date, parent, mb]
        tempdic = {}
        for i in range(0, 8):
            tempdic[column_headers[i]] = [tempdatalist[i]]
        tempdf = pd.DataFrame.from_dict(tempdic)
        newordersdf = newordersdf.copy().append(tempdf.copy())
        # print('newordersdf')
        # print(newordersdf)
    # print(newordersdf)
    return newordersdf.copy()

"""Create what if order."""
def create_phantom_order(bompart, qty, completiondate, bomsdf, missingbomlist, manybomlist):
    column_headers = ['ORDER', 'ITEM', 'ORDERTYPE', 'PART', 'QTYREMAINING', 'DATESCHEDULED', 'PARENT', 'Make/Buy']
    neworderdf = pd.DataFrame(columns=column_headers)
    order = fs.Index().show_fake_index()
    item = 'Imaginary'
    ordertype = 'Finished Good'
    parent = order
    mb = 'Make'
    tempdatalist = [order, item, ordertype, bompart, qty, completiondate, parent, mb]
    tempdic = {}
    for i in range(0, 8):
        tempdic[column_headers[i]] = [tempdatalist[i]]
    bompartdf = pd.DataFrame.from_dict(tempdic)
    neworderdf = neworderdf.append(bompartdf)
    bompartdf['DATESCHEDULED'] = bompartdf['DATESCHEDULED'] + dt.timedelta(days=1)
    bomdf = bom.order_exploder_new_order(bomsdf, bompartdf, missingbomlist, manybomlist)
    neworderdf = neworderdf.append(bomdf)
    return neworderdf

"""Add what if order to timeline"""
def add_phantom_order(phantomdf, timeline):
    workingtimeline = timeline.append(phantomdf)
    return workingtimeline

"""Checks ending inventory to see about timing issues."""
def find_timing_issues(timeline):
    phantoms = timeline[timeline['ITEM'] == 'Phantom'].copy()  # get all phantom order lines
    reducedPhantoms = phantoms[(phantoms['ORDERTYPE'] == 'Purchase') | (phantoms['ORDERTYPE'] == 'Finished Good')].copy()  # all phantom lines except raw goods
    phantomList = reducedPhantoms['PART'].unique()  # series of any parts showing up in phantom orders
    lastinv = timeline.drop_duplicates(subset='PART', keep='last')  # final inventory of all parts
    lastinv = lastinv[['PART','INV']]  # reduced to part numbers and inventory
    phantomInv = lastinv[lastinv['PART'].isin(phantomList)]  # final inventory of only parts with phantom purchase or FG lines
    phantomInv = phantomInv[phantomInv['INV'] > 0.1]  # reduced to only parts ending with a positive inventory (or close enough, damn floats)
    timingList = phantomInv['PART'].tolist()  # convert the part numbers to a list for reference later
    return timingList

"""This loops through finding the original demand driver."""
def find_demand_driver(timeline):
    timeline = timeline.sort_values(by=['PART', 'DATESCHEDULED', 'ORDER'], ascending=[True, True, True]) ### I think sorting and reseting the index will make this all function.
    timeline.reset_index(drop=True, inplace=True)  # without reseting the index, whenever a value was assigned to GRANDPARENT, it was assigning multiple rows because of duplicate indexes.
    phantomtimelineP = timeline.ix[timeline['ITEM'] == 'Phantom']  # Grabs Phantom lines
    # print(phantomtimelineP)
    phantomtimelineI = timeline.ix[timeline['ITEM'] == 'Imaginary']  # Grabs Imaginary lines
    # print(phantomtimelineI)
    phantomtimeline = phantomtimelineP.copy().append(phantomtimelineI.copy())  # and combines 'em
    for index, row in phantomtimeline.iterrows():  # Iterates through all phantom and imaginary order lines
        if row['ORDERTYPE'] == 'Purchase':
            parentTemp = timeline.ix[timeline['ORDER'] == row['PARENT']].copy()
            parentTemp = parentTemp.ix[parentTemp['PART'] == row['PART']].copy()
            while True:
                parentTemp.reset_index(drop=True, inplace=True)
                if parentTemp.get_value(0, 'ITEM') == 'Phantom':
                    if parentTemp.get_value(0, 'ORDERTYPE') == 'Raw Good':
                        secondTempHold = timeline.ix[timeline['ORDER'] == parentTemp.get_value(0, 'ORDER')]
                        parentTemp = secondTempHold.ix[secondTempHold['ORDERTYPE'] == 'Finished Good']
                    else:
                        secondTempHold = timeline.ix[timeline['ORDER'] == parentTemp.get_value(0, 'PARENT')]
                        parentTemp = secondTempHold.ix[secondTempHold['PART'] == parentTemp.get_value(0, 'PART')]
                elif parentTemp.get_value(0, 'ITEM') == 'Imaginary':
                    if parentTemp.get_value(0, 'ORDERTYPE') == 'Raw Good':
                        secondTempHold = timeline.ix[timeline['ORDER'] == parentTemp.get_value(0, 'ORDER')]
                        parentTemp = secondTempHold.ix[secondTempHold['ORDERTYPE'] == 'Finished Good']
                    elif parentTemp.get_value(0, 'ORDER') == parentTemp.get_value(0, 'PARENT'):
                        parentTemp.reset_index(drop=True, inplace=True)
                        rowp = parentTemp.get_value(0, 'PARENT')
                        timeline.ix[index, 'GRANDPARENT'] = rowp
                        break
                    else:
                        secondTempHold = timeline.ix[timeline['ORDER'] == parentTemp.get_value(0, 'PARENT')]
                        parentTemp = secondTempHold.ix[secondTempHold['PART'] == parentTemp.get_value(0, 'PART')]
                else:
                    parentTemp.reset_index(drop=True, inplace=True)
                    rowp = parentTemp.get_value(0, 'PARENT')
                    timeline.ix[index, 'GRANDPARENT'] = rowp
                    break
        else:
            if row['ORDERTYPE'] == 'Raw Good':
                secondTempHold = timeline.ix[timeline['ORDER'] == row['ORDER']]
                parentTemp = secondTempHold.ix[secondTempHold['ORDERTYPE'] == 'Finished Good']
            else:
                parentTemp = timeline[timeline['ORDER'] == row['ORDER']]
                parentTemp = parentTemp[parentTemp['PART'] == row['PART']]
            while True:
                parentTemp.reset_index(drop=True, inplace=True)
                if parentTemp.get_value(0, 'ORDERTYPE') == 'Raw Good':
                    secondTempHold = timeline.ix[timeline['ORDER'] == parentTemp.get_value(0, 'ORDER')]
                    parentTemp = secondTempHold.ix[secondTempHold['ORDERTYPE'] == 'Finished Good']
                    parentTemp.reset_index(drop=True, inplace=True)
                if parentTemp.get_value(0, 'ITEM') == 'Phantom':
                    secondTempHold = timeline.ix[timeline['ORDER'] == parentTemp.get_value(0, 'PARENT')]
                    parentTemp = secondTempHold.ix[secondTempHold['PART'] == parentTemp.get_value(0, 'PART')]
                elif parentTemp.get_value(0, 'ITEM') == 'Imaginary':
                    if parentTemp.get_value(0, 'ORDER') == parentTemp.get_value(0, 'PARENT'):
                        timeline.ix[index, 'GRANDPARENT'] = parentTemp.get_value(0, 'PARENT')
                        break
                    else:
                        secondTempHold = timeline.ix[timeline['ORDER'] == parentTemp.get_value(0, 'PARENT')]
                        parentTemp = secondTempHold.ix[secondTempHold['PART'] == parentTemp.get_value(0, 'PART')]
                else:
                    timeline.ix[index, 'GRANDPARENT'] = parentTemp.get_value(0, 'PARENT')
                    break
    return timeline

"""Gather Phantom parts."""
def get_phantom_orders(thedf):
    phantomdf = thedf.ix[thedf['ITEM'] == 'Phantom']
    phantomdf = phantomdf.sort_values(by=['PART', 'DATESCHEDULED', 'ORDER'], ascending=[True, True, True])
    return phantomdf

"""Fills the cells in the excel workbook."""
def fill_subtotals_workbook(worksheet, thedf, format):
    columns = list(thedf.columns.values) # grabs a list of headers
    for each in columns:
        worksheet.write(0, columns.index(each), each) # writes the headers onto the first row in excel
    rowcounta = 1 # This is the holding line to track the starting line of each part's section
    uniqueA = thedf.PART.unique() # grab a list of each part
    for item in uniqueA:
        # print(item) # Use when looking for glitch
        rowcountb = 0 # This is the tracking line for the part's section.  Adding it to the holding line returns the excel line to write.
        tempAdf = thedf.ix[thedf['PART'] == item] # dataFrame for one part
        tempAdf.reset_index(drop=True, inplace=True)
        while rowcountb < len(tempAdf): # This loop runs until the tracking line is past the orders (leaving the subtotal line to fill)
            # print(rowcounta) # Use when looking for glitch
            for each in columns: # prints each cell one at a time, using the column headers for reference.
                # print(each) # Use when looking for glitch
                value = tempAdf.get_value(rowcountb, each)
                # print(value) # Use when looking for glitch
                if each == 'DATESCHEDULED': # The date column uses "write_datetime()"
                    worksheet.write_datetime((rowcounta + rowcountb), columns.index(each), value, format)
                else: # Otherwise, just use "write()"
                    worksheet.write((rowcounta + rowcountb), columns.index(each), value)
            rowcountb += 1
        rowcountat = rowcounta + rowcountb # This saves the line number where the subtotals are written
        worksheet.write(rowcountat, 3, item) # write the Part Number in the 4th column
        description = tempAdf.get_value(0, 'DESCRIPTION') # pull Part description from inital row
        worksheet.write(rowcountat, 9, description) # write description into 10th column so it's visible on the subtotal row
        rowcounta += 1 # raise the holding line by 1, because it's printing a formula ("row 1" here is "row 2" in excel formulas).
        worksheet.write_formula(rowcountat, 4, '=SUBTOTAL(9, E%s:E%s)' %(rowcounta, rowcountat)) # add subtotal formula to the 5th column
        rowcounta = rowcountat + 1 # Set holding line one past the subtotal line and start on the next part.

"""Creates the framework in the excel workbook."""
def create_subtotals_format(workbook, worksheet, thedf, timinglist):
    # These are used to mark which excel line is being pre-formatted.
    rowcounta = 1 # Tracking line: This one keeps rising and is used for the collapsable subtotal line
    rowcountb = 1 # Holding line: This one reserves the starting line for each part's section
    uniqueA = thedf.PART.unique() # stores each part number
    for item in uniqueA: # for each unique part number
        tempAdf = thedf.ix[thedf['PART'] == item] # create a dataFrame of that part's orders
        tempAdf.reset_index(drop=True, inplace=True) # reset its index
        for line in range(0, len(tempAdf)): # for each line in this part's orders
            newline = line + rowcountb # the excel line to format is the holding line number plus which row it is in the part's orders
            worksheet.set_row(newline, None, None, {'hidden': True, 'level': 2}) # set row's format (it's hidden)
            rowcounta += 1 # increase the tracking line
        if item in timinglist: # after all the part's order line formats are set, this makes the next line a subtotal line and pink (if there's a timing issue)
            timingformat = workbook.add_format()
            timingformat.set_bg_color('pink')
            worksheet.set_row((rowcounta), None, timingformat, {'level': 1, 'collapsed': True})
        else: # If there's no timing issue, this will make the next line a subtotal line but not highlight it
            worksheet.set_row((rowcounta), None, None, {'level': 1, 'collapsed': True})
        rowcounta += 1 # increase the tracking line
        rowcountb = rowcounta # set the holding line equal to tracking line.  Holding line is now set to the beginning of the next part's section.
    dateformat = workbook.add_format({'num_format': 'mm/dd/yy'}) # set date format in preparation for filling the worksheet.
    fill_subtotals_workbook(worksheet, thedf, dateformat) # this actually writes the data into the cells now that the format for each line is set.

"""Create Timeline Worksheet."""
"""Some dates are coming in as strings from the timeline.  I patched the problem below, but the root of it will persist."""
def create_timeline_worksheet(workbook, worksheet, timeline):
    dateformat = workbook.add_format({'num_format': 'mm/dd/yy'})

    timeline.reset_index(drop=True, inplace=True)
    timeline = timeline.fillna(0)

    timeline['DATESCHEDULED'] = pd.to_datetime(timeline['DATESCHEDULED'])  # BANDAID!!! Why are some of these not datetime?

    columns = list(timeline.columns.values)
    columnindex = len(columns)
    for each in range(0, columnindex):
        worksheet.write(0, each, columns[each])
    ### This next for loop is checking each row in the dataFrame (rows 0 through the total length)
    ### It looks off because the numbers listed for row are actually the excel row numbers (1 through the length plus one)
    ### Row 0 in excel is used for writing the column headers above
    for row in range(1, len(timeline)+1):
        # print('---row %s in timeline' %(row))  # Helps find problem row if there's a bug.
        for column in range(0, columnindex):
            if column == 6:  # Column 6 is "DATESCHEDULED" so this section writes a datetime.
                value = timeline.get_value(row-1, column, True)
                worksheet.write_datetime(row, column, value, dateformat)
            else:
                value = timeline.get_value(row-1, column, True)
                worksheet.write(row, column, value)

"""Splits up all the phantom orders for purchasing and manufacturing."""
def split_phantoms(phantomdf):
    purchasedf = phantomdf.ix[phantomdf['ORDERTYPE'] == 'Purchase'].copy()
    manufacturingdf = phantomdf.ix[phantomdf['ORDERTYPE'] == 'Finished Good'].copy()
    return [purchasedf, manufacturingdf]

"""Create dataframe from missing boms"""
def miss_bom_df(misslist):
    temp = {'Parts with no BOM' : misslist}
    missdf = pd.DataFrame(temp)
    return missdf

"""Creates sheet for missing boms"""
def create_miss_bom_worksheet(worksheet, parts):
    worksheet.write(0, 0, 'PartsWithNoBOM')
    row = 1
    for each in parts:
        worksheet.write(row, 0, each)
        row += 1

"""Create dataframe from too many boms"""
def many_bom_df(manylist):
    temp = {'Parts with too many BOMs' : manylist}
    manydf = pd.DataFrame(temp)
    return manydf

"""Creates sheet for too many boms"""
def create_too_many_boms_worksheet(worksheet, parts):
    worksheet.write(0, 0, 'PartsWithTooManyBOMs')
    row = 1
    for each in parts:
        worksheet.write(row, 0, each)
        row += 1

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
        tempdf = tempdf.append(currentPartOrders, ignore_index=True)  # append the current part's orders to the starting line
        tempdf.set_value(index=0, col='INV', value= tempdf['INV'].iloc[1])  # this references the inventory on the other columns to set the starting inventory
        ind = 1  # This is going to iterate through the index or rows
        while ind < len(tempdf):  # while this indexer is less than the length
            tempdf.set_value(ind, 'INV', (tempdf['INV'].iloc[ind-1] + tempdf['QTYREMAINING'].iloc[ind]))  # set the next inventory value by adding the order amount to the previous inventory value
            ind += 1  # step up the indexer
        resultdf = resultdf.append(tempdf.copy(), ignore_index=True)  # store this as a result
    return resultdf  # results are the new demand dataFrame