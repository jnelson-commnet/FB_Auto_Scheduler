__author__ = 'Chris'

import os
import sys

# Live server:
sys.path.insert(0, 'Z:\Python projects\FishbowlAPITestProject')
# Test server:
# sys.path.insert(0, 'Z:\Python projects\FB_API_TestServer')

# import connecttest

# homey = os.getcwd()
homey = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
# print('forecast api ----')
# print(homey)
redouxPath = os.path.join(homey, 'ForecastRedoux')
sqlPath = os.path.join(redouxPath, 'SQL')
rawDataPath = os.path.join(redouxPath, 'RawData')



def run_queries(queryPath, dataPath):
    myresults = connecttest.create_connection(queryPath, 'BOMQuery.txt')
    myexcel = connecttest.makeexcelsheet(myresults)
    connecttest.save_workbook(myexcel, dataPath, 'BOMs.xlsx')
    myresults = connecttest.create_connection(queryPath, 'PartQuery.txt')
    myexcel = connecttest.makeexcelsheet(myresults)
    connecttest.save_workbook(myexcel, dataPath, 'Parts.xlsx')
    myresults = connecttest.create_connection(queryPath, 'MOQueryRedoux.txt')
    myexcel = connecttest.makeexcelsheet(myresults)
    connecttest.save_workbook(myexcel, dataPath, 'MOs.xlsx')
    myresults = connecttest.create_connection(queryPath, 'POQuery.txt')
    myexcel = connecttest.makeexcelsheet(myresults)
    connecttest.save_workbook(myexcel, dataPath, 'POs.xlsx')
    myresults = connecttest.create_connection(queryPath, 'SOQuery.txt')
    myexcel = connecttest.makeexcelsheet(myresults)
    connecttest.save_workbook(myexcel, dataPath, 'SOs.xlsx')
    myresults = connecttest.create_connection(queryPath, 'INVQuery.txt')
    myexcel = connecttest.makeexcelsheet(myresults)
    connecttest.save_workbook(myexcel, dataPath, 'INVs.xlsx')
    myresults = connecttest.create_connection(queryPath, 'DescQuery.txt')
    myexcel = connecttest.makeexcelsheet(myresults)
    connecttest.save_workbook(myexcel, dataPath, 'Descs.xlsx')
    return 'Queries Successful'

