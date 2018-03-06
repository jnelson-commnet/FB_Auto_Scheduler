__author__ = 'Chris'

import pandas as pd
import datetime as dt

"""This multiplies the raw good qty by the input fg qty."""
def order_exploder(bomsdf, fgdf, ordernum, missingbomlist, manybomlist):
    column_headers = ['ORDER', 'ITEM', 'ORDERTYPE', 'PART', 'QTYREMAINING', 'DATESCHEDULED', 'PARENT', 'Make/Buy']
    workingbom = bomsdf.ix[bomsdf.FG == 10].copy()
    workingbom = workingbom.loc[workingbom['PART'] == fgdf['PART']].copy()
    workingbom.reset_index(drop=True, inplace=True)
    if len(workingbom.index) > 1:
        # print('%s has too many BOMs.' %fgdf['PART'])
        manybomlist.add_part(fgdf['PART'])
        workingbom = workingbom.ix[:1]
    partsdf = bomsdf.ix[bomsdf.FG == 20].copy()
    while True:
        try:
            workbom = workingbom['BOM'].iloc[0]
            partsdf = partsdf.loc[partsdf['BOM'] == workbom].copy()
            break
        except IndexError:
            # print('%s is missing an active BOM!' %fgdf['PART'])
            missingbomlist.add_part(fgdf['PART'])
            fake_columns = ['QTY']
            partsdf = pd.DataFrame(columns=fake_columns)
            break
    partsdf['NEWQTY'] = partsdf['QTY'] * fgdf['QTYREMAINING']
    bomdf = pd.DataFrame(columns=column_headers)
    for index, row in partsdf.iterrows():
        if fgdf['ITEM'] == 'Imaginary':
            item = 'Imaginary'
        else:
            item = 'Phantom'
        ordertype = 'Raw Good'
        part = row['PART']
        qty = row['NEWQTY']
        date = pd.to_datetime(fgdf['DATESCHEDULED']) - dt.timedelta(days=1) #This is a lead time
        parent = fgdf['ORDER']
        mb = row['Make/Buy']
        templist = [ordernum,item,ordertype,part,qty,date,parent,mb]
        tempdic = {}
        for i in range(0, 8):
            tempdic[column_headers[i]] = [templist[i]]
        tempdf = pd.DataFrame.from_dict(tempdic)
        bomdf = bomdf.append(tempdf)
    return bomdf.copy()

def order_exploder_new_order(bomsdf, fgdf, missingbomlist, manybomlist):
    column_headers = ['ORDER', 'ITEM', 'ORDERTYPE', 'PART', 'QTYREMAINING', 'DATESCHEDULED', 'PARENT', 'Make/Buy']
    workingbom = bomsdf.ix[bomsdf.FG == 10].copy()
    fgdf.reset_index(drop=True, inplace=True)
    workingbom = workingbom.loc[workingbom['PART'] == fgdf.iloc[0]['PART']].copy()
    workingbom.reset_index(drop=True, inplace=True)
    if len(workingbom.index) > 1:
        manybomlist.add_part(fgdf['PART'])
        workingbom = workingbom.iloc[0]
    partsdf = bomsdf.ix[bomsdf.FG == 20].copy()
    while True:
        try:
            # print('*** finding problem spot ***')
            # print(workingbom.iloc[0]['BOM'])
            # Warning: this can break if there are multiple active BOMs to produce a part!
            partsdf = partsdf.loc[partsdf['BOM'] == workingbom.iloc[0]['BOM']].copy()
            break
        except IndexError:
            ''' If an imaginary build doesn't have a BOM, this will print it and save it to the "missing BOMs list"
                Note that the script will probably fail when saving to Excel. '''
            print('%s is missing an active BOM!' %fgdf['PART'])
            missingbomlist.add_part(fgdf['PART'])
            fake_columns = ['QTY']
            partsdf = pd.DataFrame(columns=fake_columns)
            break
    partsdf['NEWQTY'] = partsdf['QTY'] * fgdf.iloc[0]['QTYREMAINING']
    bomdf = pd.DataFrame(columns=column_headers)
    for index, row in partsdf.iterrows():
        order = fgdf.iloc[0]['ORDER']
        item = 'Imaginary'
        ordertype = 'Raw Good'
        part = partsdf.ix[index]['PART']
        qty = (partsdf.ix[index]['NEWQTY'] * -1)
        date = pd.to_datetime(fgdf.iloc[0]['DATESCHEDULED']) - dt.timedelta(days=1)
        parent = fgdf.iloc[0]['ORDER']
        mb = partsdf.ix[index]['Make/Buy']
        templist = [order,item,ordertype,part,qty,date,parent,mb]
        tempdic = {}
        for i in range(0, 8):
            tempdic[column_headers[i]] = [templist[i]]
        tempdf = pd.DataFrame.from_dict(tempdic)
        bomdf = bomdf.append(tempdf)
    return bomdf