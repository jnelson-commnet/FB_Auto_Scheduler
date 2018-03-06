__author__ = 'Chris'

import ForecastMain as fm
import pandas as pd
import ForecastTimelineBackend as ftlb
import ForecastAPI
import ForecastSettings as fs
import xlsxwriter
import time

start = time.time()

# sql = ForecastAPI.run_queries() #Runs the function in ForecastAPI that pulls data from Fishbowl
# print(sql) #Prints Queries Successful!

datalist = fm.data_prep()
"""
returns:
datalist[0] = newordersdf
datalist[1] = invdf
datalist[2] = bomsdf
"""
normal_orders = [datalist[0], datalist[1]] # newordersdf, invdf
invdf = datalist[1]
startinginvdf = datalist[1].copy()
bomsdf = datalist[2]
mypartsdf = fm.gather_parts()

# print('saving files in case thar be a bug')
# writer = pd.ExcelWriter('Z:\Python projects\Chris Forecast\Forecast\\BugSearch.xlsx', engine='xlsxwriter')
# datalist[0].to_excel(writer, sheet_name='newordersdf')
# datalist[1].to_excel(writer, sheet_name='invdf')
# datalist[2].to_excel(writer, sheet_name='bomsdf')
# writer.save()



print('--- Runtime: %s mins ---' %((time.time() - start)/60))

print('going into create_bom_tiers')
mytierlist = ftlb.create_bom_tiers_v2(bomsdf, mypartsdf)


print('--- Runtime: %s mins ---' %((time.time() - start)/60))
print('out of create_bom_tiers')

# tempsave = pd.DataFrame.from_dict(mytierlist, orient='index')  # getting a peek at mytierlist
# tempsave = tempsave.transpose()
# writer = pd.ExcelWriter('Z:\Python projects\Chris Forecast\Forecast\PartTierTest2.xlsx', engine='xlsxwriter')
# tempsave.to_excel(writer, sheet_name='Sheet', index=False)
# writer.save()

# tiersdf = pd.read_excel('Z:\Python projects\Chris Forecast\Forecast\PartTierTest.xlsx', sheetname='Sheet')
# mytierlist = tiersdf.to_dict('list')

writer = pd.ExcelWriter('Z:\Python projects\Chris Forecast\Forecast\BugSearchOrders.xlsx', engine='xlsxwriter')  # temporary to see how this thing works

missingboms = fs.No_BOMs()  # Creates an instance of the class in Forecast Settings No_BOMs
manyboms = fs.Many_BOMs()  # Creates an instance of the class in Forecast Settings Many_BOMs
tier = 1
while len(mytierlist) > 0:
	print('--- Runtime: %s mins ---' %((time.time() - start)/60))
	print('Running tier', tier)
	# tierlist = mytierlist['Tier%d' %(tier)]
	tierlist = mytierlist[tier]
	normal_orders = fm.complete_orders_loop_redux(tierlist, normal_orders[0].copy(), invdf, bomsdf, missingboms, manyboms)  # Runs the function that actually builds out the timeline
	normal_orders[0] = normal_orders[0].copy().append(normal_orders[2].copy())
	# print('Tier')
	# print(tier)
	# print(normal_orders[0])
	# print(normal_orders[2])
	# del mytierlist['Tier%d' %(tier)]
	normal_orders[0].to_excel(writer, sheet_name='final %s' %(tier), index=False)  # temporary to check how these things work
	normal_orders[1].to_excel(writer, sheet_name='short %s' %(tier), index=False)  # temporary to check how these things work
	normal_orders[2].to_excel(writer, sheet_name='orders %s' %(tier), index=False)  # temporary to check how these things work
	del mytierlist[tier]
	tier += 1

writer.save()  # temporary for the section above


writer = pd.ExcelWriter('Z:\Python projects\Chris Forecast\Forecast\BugSearch3.xlsx', engine='xlsxwriter')  # temporary to see how this thing works
normal_orders[0].to_excel(writer, sheet_name='fina', index=False)  # temporary to check how these things work
writer.save()  # temporary for the section above
print('saved?')

print('*Timeline Has Been Created*')
print('--- Runtime: %s mins ---' %((time.time() - start)/60))

timingtest = ftlb.find_timing_issues(normal_orders[0], normal_orders[1])  # Finds parts that have phantom orders and are left with a positive inventory
# print(timingtest)  # Just looking, can delete

demand = ftlb.find_demand_driver(normal_orders[0])  # Runs the loop that figures out the top level driver for all the orders
phantoms = ftlb.get_phantom_orders(demand)  # Returns all the phantom orders

writer = pd.ExcelWriter('Z:\Python projects\Chris Forecast\Forecast\mytimelinetest.xlsx')  # Creates a test excel file
demand.to_excel(writer, 'Sheet')  # Fills the test excel with the whole timeline
writer.save()



# adds an inventory counter to the timeline
demand = ftlb.add_inv_counter(inputTimeline=demand, backdate='1999-12-31 00:00:00', invdf=startinginvdf)






workbook = xlsxwriter.Workbook('Z:\Python projects\Chris Forecast\Forecast\RegularForecast.xlsx')  # Create the actual final product excel file
orderslist = ftlb.split_phantoms(phantoms)  # Seperates purchase and manufacture phantom orders
worksheetP = workbook.add_worksheet('Purchasing')  # Create the seperate worksheets for purchasing and manufacturing
worksheetM = workbook.add_worksheet('Manufacturing')

"""experimental code section, trying to add part descriptions to MFG worksheet"""
descdf = pd.read_excel('Z:\Python projects\Chris Forecast\Forecast\ForecastRedoux\RawData\Descs.xlsx', header=0)
orderslist[0] = pd.merge(orderslist[0].copy(), descdf.copy(), how='left', on='PART')
orderslist[1] = pd.merge(orderslist[1].copy(), descdf.copy(), how='left', on='PART')
columnList = ['ORDER', 'ITEM', 'ORDERTYPE', 'PART', 'QTYREMAINING', 'DATESCHEDULED', 'PARENT', 'Make/Buy', 'GRANDPARENT', 'DESCRIPTION']
orderslist[0] = orderslist[0][columnList]
orderslist[1] = orderslist[1][columnList]


ftlb.create_subtotals_format(workbook=workbook, worksheet=worksheetP, thedf=orderslist[0], timinglist=timingtest)  # This function creates the subtotals in the worksheet
ftlb.create_subtotals_format(workbook=workbook, worksheet=worksheetM, thedf=orderslist[1], timinglist=timingtest)  # Then is calls another function to add the data in FTLB
worksheetT = workbook.add_worksheet('Timeline')  # Adds another worksheet for the timeline

demand = pd.merge(demand.copy(), descdf.copy(), how='left', on='PART')
demand.sort_values(by=['PART', 'DATESCHEDULED'], ascending=[True, True], inplace=True)
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


### This is getting saved to use for other reports
writer = pd.ExcelWriter('Z:\Python projects\Chris Forecast\Forecast\demand.xlsx')
demand.to_excel(writer, 'timeline')
writer.save()

print('*The forecast is done!*')