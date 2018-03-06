__author__ = 'Chris'

import ForecastAPI
import os
import pandas as pd
import ForecastTimelineBackend as ftlb
import ForecastSettings as fs
import xlsxwriter
import datetime as dt

# homey = os.getcwd() # not working on Pi
homey = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
redouxPath = os.path.join(homey, 'ForecastRedoux')
rawDataPath = os.path.join(redouxPath, 'RawData')
AdditionalInfoPath = os.path.join(homey, 'AdditionalInfo')

"""Pull the orders data"""
# giving the option to substitute a dataFrame of MO orders and to not include SOs.
def gather_orders(dataPath, includeSO=True, subMO=None):
    if subMO is not None:
        modf = subMO.copy()
    else:
        mopath = os.path.join(dataPath, 'MOs.xlsx')
        modf = pd.read_excel(mopath, header=0) #Opens and puts the data into a dataframe
    orgdf = ftlb.create_mo_parents(modf)
    popath = os.path.join(dataPath, 'POs.xlsx')
    tempdf = pd.read_excel(popath, header=0) #Opens and puts the data into a dataframe
    orgdf = orgdf.append(tempdf.copy()) #Append all the data into one dataframe
    if includeSO == True:
        sopath = os.path.join(dataPath, 'SOs.xlsx')
        tempdf = pd.read_excel(sopath, header=0) #Opens and puts the data into a dataframe
    orgdf = orgdf.append(tempdf.copy()) #Append all the data into one dataframe
    orgdf = orgdf.sort_values(by=['PART', 'DATESCHEDULED'], ascending=[True, False]) #Sort the data by part then date
    return orgdf

"""Pull the parts data"""
def gather_parts(dataPath):
    partspath = os.path.join(dataPath, 'Parts.xlsx')
    partsdf = pd.read_excel(partspath) #Opens and puts the data into a dataframe
    partsdf = partsdf.sort_values(by='PART', ascending=True) #Sort the data by part
    return partsdf

"""Pull the inventory data"""
def gather_inventory(dataPath):
    invpath = os.path.join(dataPath, 'INVs.xlsx')
    orgdf = pd.read_excel(invpath, header=0) #Opens and puts the data into a dataframe
    orgdf = orgdf.sort_values(by='PART', ascending=True) #Sort the data by part
    return orgdf

"""Converts quantities to the default unit of measure for each part
    uomid 1 is 'ea'
    uomid 2 is 'ft'
    uomid 7 is 'in' """
def fix_uom(orgdf):
    uomIssues = orgdf[orgdf['BOMUOM'] != orgdf['PARTUOM']].copy()
    for index, row in uomIssues.iterrows():
        if (row['BOMUOM'] == 1 and row['PARTUOM'] == 2): # if BOM is 'ea' and part is 'ft' then multiply by 2
            orgdf.set_value(index, 'QTY', (row['QTY'] * 2))
        elif (row['BOMUOM'] == 2 and row['PARTUOM'] == 1): # if BOM is 'ft' and part is 'ea' then divide by 2
            orgdf.set_value(index, 'QTY', (row['QTY'] / 2))
        elif (row['BOMUOM'] == 2 and row['PARTUOM'] == 7): # if BOM is 'ft' and part is 'in' then multiply by 12
            orgdf.set_value(index, 'QTY', (row['QTY'] * 12))
        elif (row['BOMUOM'] == 7 and row['PARTUOM'] == 2): # if BOM is 'in' and part is 'ft' then divide by 12
            orgdf.set_value(index, 'QTY', (row['QTY'] / 12))
    return(orgdf.copy())

"""Pull the BOM data"""
def gather_boms(dataPath):
    bompath = os.path.join(dataPath, 'BOMs.xlsx')
    orgdf = pd.read_excel(bompath, header=0) #Opens and puts the data into a dataframe
    orgdf = fix_uom(orgdf) # edits quantities to match default UOM
    orgdf.drop(['BOMUOM','PARTUOM'], axis=1, inplace=True) # drops UOM reference columns
    orgdf = orgdf.sort_values(by=['BOM','FG','PART'], ascending=[True,True,True]) #Sort the data by bom, finished good, then part
    return orgdf

"""Create make/buy table."""
def make_buy(mbdf):
    mbdf = mbdf.drop('AvgCost', axis=1) #Drop the avg cost column. If we want to use this later we can
    mbdf = mbdf.sort_values(by='PART', ascending=True) #Sort the data by part
    mbdf = mbdf.drop_duplicates('PART') #Don't think this is actually neccesary
    return mbdf

"""Add make/buy column to main table."""
def add_make_buy(orgdf, mbdf):
    newdf = pd.merge(orgdf, mbdf, on='PART', how='left') #Add on the make buy column to the regular orders dataframe
    return newdf

"""Adds new orders to original orders"""
def add_new_orders(ordersdf, newordersdf):
    allordersdf = ordersdf.append(newordersdf) #Add the new orders created from shortages
    allordersdf.reset_index(drop=True, inplace=True)
    # print(allordersdf)
    return allordersdf.copy()

"""Just combining all the data pulling functions. This isn't used.
    It's just a quick function to combine all the data gathering functions."""
def data_prep(dataPath, includeSO=True, subMO=None):
    ordersdf = gather_orders(dataPath=dataPath, includeSO=includeSO, subMO=subMO)
    partsdf = gather_parts(dataPath)
    mbdf = make_buy(partsdf)
    newordersdf = add_make_buy(ordersdf, mbdf)
    invdf = gather_inventory(dataPath)
    bomsdf = gather_boms(dataPath)
    return [newordersdf, invdf, bomsdf]

"""
To avoid extra orders due to scheduling issues, this can be run after data_prep().
It takes all the positive inventory changes and bumps them back a few years earlier (so PO's are counted first before usage).
"""
def bandaid_schedule_issues(ordersdf):
    past = ordersdf[ordersdf['QTYREMAINING'] > 0].copy()  # all positive inv changes
    future = ordersdf[ordersdf['QTYREMAINING'] < 0].copy()  # all negative inv changes
    today = dt.datetime.now()  # grab today's date
    yesteryear = today + dt.timedelta(days=-2000)  # bump it back a few years
    past['DATESCHEDULED'] = yesteryear.strftime('%Y-%m-%d %H:%M:%S')  # copy it into the positive inv changes
    ordersdf = past.copy().append(future.copy())  # append all inv changes back together (will have dropped anything equal to 0)
    ordersdf.sort_values(by=['PART', 'DATESCHEDULED'], ascending=[True, False], inplace=True)  # sort it
    return ordersdf


"""Loops to capture all orders for different tiers"""
def complete_orders_loop_redux(partlist, ordersdf, invdf, bomsdf, missingboms, manyboms):
    column_headers = ['ORDER', 'ITEM', 'ORDERTYPE', 'PART', 'QTYREMAINING', 'DATESCHEDULED', 'PARENT', 'Make/Buy'] #Create Headers list for future use
    newordersdf = pd.DataFrame(columns=column_headers)  # Save an empty dataframe with pre set column headers, the orders to run will be saved here consecutively.
    ordersdf.reset_index(drop=True, inplace=True)
    # partlist = [x for x in partlist if str(x) != 'nan'] #Only for excel  ### I don't think this is necessary on a full run, just when saving state with excel - Jack
    for index, each in ordersdf.iterrows():  # Checking every row in ordersdf
        if str(each['PART']) in partlist:  # If the part number in ordersdf is also in the current tierlist of parts to run ...
            templist = [each['ORDER'], each['ITEM'], each['ORDERTYPE'], each['PART'], each['QTYREMAINING'], each['DATESCHEDULED'], each['PARENT'], each['Make/Buy']]  # then save that row ...
            newordersdf.loc[len(newordersdf)] = templist  # and add it to newordersdf.
            ordersdf.drop([index], inplace=True)  # drop it from the original orderlist to avoid revisiting it ### I'm not sure how this line is needed yet - Jack
            # print(newordersdf)
    finalordersdf = pd.DataFrame(columns=column_headers) #Create dataframe which will be the final product
    # print(newordersdf)
    shortorderslist = ftlb.find_next_shortage_redux(invdf, newordersdf, partlist) #This returns the list below and finds the shortages for every part
    # shortagedf = shortorderslist[0]
    # postordersdf = shortorderslist[1]
    # preordersdf = shortorderslist[2]
    # invdf = shortorderslist[3]
    finalordersdf = finalordersdf.copy().append(shortorderslist[2].copy()) #Append the orders covered by inventory
    neworders = ftlb.make_new_orders(shortorderslist[0].copy(), bomsdf.copy(), missingboms, manyboms) #Make phantom orders to make up for the shortages
    shortorderslist[1] = add_new_orders(shortorderslist[1].copy(), neworders.copy()) #Append the phantom orders to the orders timeline
    # print(shortorderslist[1])
    while shortorderslist[1].empty == False: #Run this loop until there are no more orders left to parse through
        # print(shortorderslist[0])
        shortorderslist = ftlb.find_next_shortage_redux(shortorderslist[3], shortorderslist[1], partlist) #Finds shortages for every part
        finalordersdf = finalordersdf.copy().append(shortorderslist[2].copy()) #Appends the covered orders to the final product
        if shortorderslist[0].empty: #If there are no shortages break the loop
            break
        neworders = ftlb.make_new_orders(shortorderslist[0].copy(), bomsdf.copy(), missingboms, manyboms) #Make phantom orders from the shortages
        shortorderslist[1] = add_new_orders(shortorderslist[1].copy(), neworders.copy()) #Add the phantom orders to the orders timeline
        # print(shortorderslist[1])
    # print(shortorderslist[1])
    ordersdf = ordersdf.copy().append(shortorderslist[1].copy()) # This S.O.B. took me a while to track down ... just added this so new orders pass to the next tier ... damn
    finalordersdf = finalordersdf.sort_values(by=['PART', 'DATESCHEDULED'], ascending=[True, True])
    finalordersdf.reset_index(drop=True, inplace=True) #Finally sort and reindex the final product to return
    # print(ordersdf)
    return [finalordersdf.copy(), shortorderslist[3].copy(), ordersdf.copy()]


"""Add fake orders to the orders list to simulate stock builds"""
def stitch_builds_to_orders(newOrders, boms, missingboms, manyboms):
    newbuilds = pd.read_excel(os.path.join(AdditionalInfoPath, 'PartsToBuild.xlsx'), sheetname='Sheet1')
    for index, row in newbuilds.iterrows():
        bomnum = row['Part']
        bomqty = row['Qty']
        bomdate = row['Date']
        bomdate = dt.datetime.strptime(bomdate, '%Y-%m-%d')
        bomorderdf = ftlb.create_phantom_order(bomnum, bomqty, bomdate, boms, missingboms, manyboms)
        newOrders = ftlb.add_phantom_order(bomorderdf, newOrders.copy())
    return newOrders


"""Run forecast with a tiered list of parts.  The tiered list helps prevent orders being attributed to the wrong "Grandparents".
   This pulls up to date info from Fishbowl, runs it, and saves it to an excel file."""
def run_normal_forecast_tiers_v2(ignore_schedule_errors=False, add_stock_builds=False, ignore_orders=False, sql_queries=True):
    if sql_queries==True:
        sql = ForecastAPI.run_queries() #Runs the function in ForecastAPI that pulls data from Fishbowl
        print(sql) #Prints Queries Successful!
    else:
        print('!Not pulling fresh data from FB!')

    missingboms = fs.No_BOMs()  # Creates an instance of the class in Forecast Settings No_BOMs
    manyboms = fs.Many_BOMs()  # Creates an instance of the class in Forecast Settings Many_BOMs

    datalist = data_prep(rawDataPath)
    """
    returns:
    datalist[0] = newordersdf
    datalist[1] = invdf
    datalist[2] = bomsdf
    """

    """ If schedule issues aren't your thing, pass ignore_schedule_errors=True when you call the funtion. """
    if ignore_schedule_errors==True:
        print('adjusting schedule to avoid issues ...')
        datalist[0] = bandaid_schedule_issues(datalist[0])  # <----- This is the only unique line to trick the forecast.
                                                            #        It bumps orders that increase inventory about 5 years in the past so they resolve first.
                                                            #        It's not perfect, I think it might make excess schedule issues for make items.  Haven't proven it yet.


    """ If you want to ignore some of the orders currently showing in FB, set ignore_orders=True.
        This pulls its list to ignore from the OrdersToRemove.xlsx spreadsheet. """
    if ignore_orders==True:
        droporders = pd.read_excel(os.path.join(AdditionalInfoPath, 'OrdersToRemove.xlsx'), sheetname='Sheet1')
        for item, row in droporders.iterrows():
            if row['OrderType'] == 'MO':
                datalist[0] = datalist[0].ix[datalist[0]['ITEM'] != row['OrderNum']].copy()
            else:
                datalist[0] = datalist[0].ix[datalist[0]['ORDER'] != str(row['OrderNum'])].copy()
        print('Excess orders removed ...')

    """ If you want to add some imaginary build amounts, pass add_stock_builds=True when you call the function.
        This pulls it's info from the PartsToBuild.xlsx spreadsheet.
        Note that the script will eventually fail if any of the parts in this list do not have an active BOM. """
    if add_stock_builds==True:
        datalist[0] = stitch_builds_to_orders(datalist[0].copy(), datalist[2].copy(), missingboms, manyboms)
        print('Imaginary builds added ...')

    # print(datalist[0])


    normal_orders = [datalist[0], datalist[1]]  # newordersdf, invdf
    invdf = datalist[1]
    startinginvdf = datalist[1].copy() # invdf is going to change throughout, this is a reference for adding and inventory counter to the timeline later
    bomsdf = datalist[2]
    mypartsdf = gather_parts()


    print('going into create_bom_tiers')
    mytierlist = ftlb.create_bom_tiers_v2(bomsdf, mypartsdf)
    print('out of create_bom_tiers')


    tier = 1
    while len(mytierlist) > 0:
        print('Running tier', tier)
        tierlist = mytierlist[tier]
        normal_orders = complete_orders_loop_redux(tierlist, normal_orders[0], invdf, bomsdf, missingboms, manyboms)  # Runs the function that actually builds out the timeline
        normal_orders[0] = normal_orders[0].append(normal_orders[2])
        del mytierlist[tier]
        tier += 1


    print('*Timeline Has Been Created*')



    demand = ftlb.find_demand_driver(normal_orders[0])  # Runs the loop that figures out the top level driver for all the orders
    phantoms = ftlb.get_phantom_orders(demand)  # Returns all the phantom orders

    writer = pd.ExcelWriter(os.path.join(homey, 'mytimelinetest.xlsx'))  # Creates a test excel file
    demand.to_excel(writer, 'Sheet')  # Fills the test excel with the whole timeline
    writer.save()

    print('Saved mytimelinetest.xlsx')

    demand = ftlb.add_inv_counter(inputTimeline=demand, backdate='1999-12-31 00:00:00', invdf=startinginvdf)  # This adds the column that shows actual inventory of a part through its orders on the timeline

    ### Timing test is borked!!!  Definitely should tie it into add_inv_counter result when reworking.
    timingtest = ftlb.find_timing_issues(demand.copy())  # Finds parts that have phantom orders and are left with a positive inventory

    workbook = xlsxwriter.Workbook(os.path.join(homey,'RegularForecast.xlsx'))  # Create the actual final product excel file
    orderslist = ftlb.split_phantoms(phantoms)  # Seperates purchase and manufacture phantom orders
    worksheetP = workbook.add_worksheet('Purchasing')  # Create the seperate worksheets for purchasing and manufacturing
    worksheetM = workbook.add_worksheet('Manufacturing')

    """experimental code section, trying to add part descriptions to MFG worksheet"""
    descdf = pd.read_excel(os.path.join(rawDataPath, 'Descs.xlsx'), header=0)
    orderslist[0] = pd.merge(orderslist[0].copy(), descdf.copy(), how='left', on='PART')
    orderslist[1] = pd.merge(orderslist[1].copy(), descdf.copy(), how='left', on='PART')
    columnList = ['ORDER', 'ITEM', 'ORDERTYPE', 'PART', 'QTYREMAINING', 'DATESCHEDULED', 'PARENT', 'Make/Buy', 'GRANDPARENT', 'DESCRIPTION']
    orderslist[0] = orderslist[0][columnList]
    orderslist[1] = orderslist[1][columnList]
    """seems to be working ... keeping it."""

    ftlb.create_subtotals_format(workbook=workbook, worksheet=worksheetP, thedf=orderslist[0], timinglist=timingtest)  # This function creates the subtotals in the worksheet
    ftlb.create_subtotals_format(workbook=workbook, worksheet=worksheetM, thedf=orderslist[1], timinglist=timingtest)  # Then is calls another function to add the data in FTLB
    worksheetT = workbook.add_worksheet('Timeline')  # Adds another worksheet for the timeline

    print('Subtotal sheets created ...')

    demand = pd.merge(demand.copy(), descdf.copy(), how='left', on='PART')  # Adding descriptions to timeline
    demand.sort_values(by=['PART', 'DATESCHEDULED'], ascending=[True, True], inplace=True)  #  Resorting it for readability before saving
    newColHeaders = ['ORDER', 'ITEM', 'ORDERTYPE', 'PART', 'QTYREMAINING', 'INV', 'DATESCHEDULED', 'PARENT', 'Make/Buy', 'GRANDPARENT', 'DESCRIPTION']
    demand = demand[newColHeaders]

    ###
    ftlb.create_timeline_worksheet(workbook, worksheetT, demand)  # Fills the timeline worksheet with data
    ###

    worksheetN = workbook.add_worksheet('PartsWithNoBOM')  # Adds another worksheet for No BOMs
    noboms = missingboms.get_parts()  # Returns the parts with no BOMs
    ftlb.create_miss_bom_worksheet(worksheetN, noboms)  # Fills the worksheet with data
    worksheetL = workbook.add_worksheet('PartsWithTooManyBOMs')  # Creates another worksheet for too many BOMs
    lotsboms = manyboms.get_parts()  # Returns the parts with many active BOMs
    ftlb.create_too_many_boms_worksheet(worksheetL, lotsboms)  # Fills the worksheet with data
    workbook.close()  # Closing the workbook commits all the data

    print('workbook closed')

    # Saving a copy of the end timeline as "demand.xlsx" to use in other projects.
    writer = pd.ExcelWriter(os.path.join(homey,'demand.xlsx'))
    demand.to_excel(writer, 'timeline')
    writer.save()

    print('*The forecast is done!*')



def run_normal_forecast_tiers_v3(dataPath, 
                                 ignore_schedule_errors=False, 
                                 add_stock_builds=False, 
                                 ignore_orders=False, 
                                 sql_queries=True, 
                                 includeSO=True,
                                 subMO=None
    ):
    # if sql_queries==True:
    #     sql = ForecastAPI.run_queries() #Runs the function in ForecastAPI that pulls data from Fishbowl
    #     print(sql) #Prints Queries Successful!
    # else:
    #     print('!Not pulling fresh data from FB!')

    missingboms = fs.No_BOMs()  # Creates an instance of the class in Forecast Settings No_BOMs
    manyboms = fs.Many_BOMs()  # Creates an instance of the class in Forecast Settings Many_BOMs

    # retooling this so the path is input and it also has the option to not include SOs
    datalist = data_prep(dataPath=dataPath, includeSO=includeSO, subMO=subMO)
    """
    returns:
    datalist[0] = newordersdf
    datalist[1] = invdf
    datalist[2] = bomsdf
    """

    """ If schedule issues aren't your thing, pass ignore_schedule_errors=True when you call the funtion. """
    if ignore_schedule_errors==True:
        print('adjusting schedule to avoid issues ...')
        datalist[0] = bandaid_schedule_issues(datalist[0])  # <----- This is the only unique line to trick the forecast.
                                                            #        It bumps orders that increase inventory about 5 years in the past so they resolve first.
                                                            #        It's not perfect, I think it might make excess schedule issues for make items.  Haven't proven it yet.


    """ If you want to ignore some of the orders currently showing in FB, set ignore_orders=True.
        This pulls its list to ignore from the OrdersToRemove.xlsx spreadsheet. """
    if ignore_orders==True:
        droporders = pd.read_excel(os.path.join(AdditionalInfoPath, 'OrdersToRemove.xlsx'), sheetname='Sheet1')
        for item, row in droporders.iterrows():
            if row['OrderType'] == 'MO':
                datalist[0] = datalist[0].ix[datalist[0]['ITEM'] != row['OrderNum']].copy()
            else:
                datalist[0] = datalist[0].ix[datalist[0]['ORDER'] != str(row['OrderNum'])].copy()
        print('Excess orders removed ...')

    """ If you want to add some imaginary build amounts, pass add_stock_builds=True when you call the function.
        This pulls it's info from the PartsToBuild.xlsx spreadsheet.
        Note that the script will eventually fail if any of the parts in this list do not have an active BOM. """
    if add_stock_builds==True:
        datalist[0] = stitch_builds_to_orders(datalist[0].copy(), datalist[2].copy(), missingboms, manyboms)
        print('Imaginary builds added ...')

    # print(datalist[0])


    normal_orders = [datalist[0], datalist[1]]  # newordersdf, invdf
    invdf = datalist[1]
    startinginvdf = datalist[1].copy() # invdf is going to change throughout, this is a reference for adding and inventory counter to the timeline later
    bomsdf = datalist[2]
    mypartsdf = gather_parts(dataPath=dataPath)


    print('going into create_bom_tiers')
    mytierlist = ftlb.create_bom_tiers_v2(bomsdf, mypartsdf)
    print('out of create_bom_tiers')


    tier = 1
    while len(mytierlist) > 0:
        print('Running tier', tier)
        tierlist = mytierlist[tier]
        normal_orders = complete_orders_loop_redux(tierlist, normal_orders[0], invdf, bomsdf, missingboms, manyboms)  # Runs the function that actually builds out the timeline
        normal_orders[0] = normal_orders[0].append(normal_orders[2])
        del mytierlist[tier]
        tier += 1


    print('*Timeline Has Been Created*')



    demand = ftlb.find_demand_driver(normal_orders[0])  # Runs the loop that figures out the top level driver for all the orders
    phantoms = ftlb.get_phantom_orders(demand)  # Returns all the phantom orders

    return demand.copy()

    # writer = pd.ExcelWriter(os.path.join(homey, 'mytimelinetest.xlsx'))  # Creates a test excel file
    # demand.to_excel(writer, 'Sheet')  # Fills the test excel with the whole timeline
    # writer.save()

    # print('Saved mytimelinetest.xlsx')

    # demand = ftlb.add_inv_counter(inputTimeline=demand, backdate='1999-12-31 00:00:00', invdf=startinginvdf)  # This adds the column that shows actual inventory of a part through its orders on the timeline

    # ### Timing test is borked!!!  Definitely should tie it into add_inv_counter result when reworking.
    # timingtest = ftlb.find_timing_issues(demand.copy())  # Finds parts that have phantom orders and are left with a positive inventory

    # workbook = xlsxwriter.Workbook(os.path.join(homey,'RegularForecast.xlsx'))  # Create the actual final product excel file
    # orderslist = ftlb.split_phantoms(phantoms)  # Seperates purchase and manufacture phantom orders
    # worksheetP = workbook.add_worksheet('Purchasing')  # Create the seperate worksheets for purchasing and manufacturing
    # worksheetM = workbook.add_worksheet('Manufacturing')

    # """experimental code section, trying to add part descriptions to MFG worksheet"""
    # descdf = pd.read_excel(os.path.join(rawDataPath, 'Descs.xlsx'), header=0)
    # orderslist[0] = pd.merge(orderslist[0].copy(), descdf.copy(), how='left', on='PART')
    # orderslist[1] = pd.merge(orderslist[1].copy(), descdf.copy(), how='left', on='PART')
    # columnList = ['ORDER', 'ITEM', 'ORDERTYPE', 'PART', 'QTYREMAINING', 'DATESCHEDULED', 'PARENT', 'Make/Buy', 'GRANDPARENT', 'DESCRIPTION']
    # orderslist[0] = orderslist[0][columnList]
    # orderslist[1] = orderslist[1][columnList]
    # """seems to be working ... keeping it."""

    # ftlb.create_subtotals_format(workbook=workbook, worksheet=worksheetP, thedf=orderslist[0], timinglist=timingtest)  # This function creates the subtotals in the worksheet
    # ftlb.create_subtotals_format(workbook=workbook, worksheet=worksheetM, thedf=orderslist[1], timinglist=timingtest)  # Then is calls another function to add the data in FTLB
    # worksheetT = workbook.add_worksheet('Timeline')  # Adds another worksheet for the timeline

    # print('Subtotal sheets created ...')

    # demand = pd.merge(demand.copy(), descdf.copy(), how='left', on='PART')  # Adding descriptions to timeline
    # demand.sort_values(by=['PART', 'DATESCHEDULED'], ascending=[True, True], inplace=True)  #  Resorting it for readability before saving
    # newColHeaders = ['ORDER', 'ITEM', 'ORDERTYPE', 'PART', 'QTYREMAINING', 'INV', 'DATESCHEDULED', 'PARENT', 'Make/Buy', 'GRANDPARENT', 'DESCRIPTION']
    # demand = demand[newColHeaders]

    # ###
    # ftlb.create_timeline_worksheet(workbook, worksheetT, demand)  # Fills the timeline worksheet with data
    # ###

    # worksheetN = workbook.add_worksheet('PartsWithNoBOM')  # Adds another worksheet for No BOMs
    # noboms = missingboms.get_parts()  # Returns the parts with no BOMs
    # ftlb.create_miss_bom_worksheet(worksheetN, noboms)  # Fills the worksheet with data
    # worksheetL = workbook.add_worksheet('PartsWithTooManyBOMs')  # Creates another worksheet for too many BOMs
    # lotsboms = manyboms.get_parts()  # Returns the parts with many active BOMs
    # ftlb.create_too_many_boms_worksheet(worksheetL, lotsboms)  # Fills the worksheet with data
    # workbook.close()  # Closing the workbook commits all the data

    # print('workbook closed')

    # # Saving a copy of the end timeline as "demand.xlsx" to use in other projects.
    # writer = pd.ExcelWriter(os.path.join(homey,'demand.xlsx'))
    # demand.to_excel(writer, 'timeline')
    # writer.save()

    # print('*The forecast is done!*')