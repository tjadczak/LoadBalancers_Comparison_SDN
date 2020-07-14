#!/usr/bin/python3.7
import os, fnmatch
import re
import fcntl
import array
import time
import random
import csv
from openpyxl import Workbook
from openpyxl import load_workbook

print("*** XLSX MAGIC ***")
for filename in fnmatch.filter(os.listdir('.'), 'results*.xlsx'):
    results = load_workbook(filename)
    results_sheet = results.active
    for column in range(1,12):
        values=[]
        for row in range(1,30):
            current_value = results_sheet.cell(row=row, column=column).value
            if current_value:
                results_sheet.cell(row=row, column=column, value=float(current_value))
                values.append(float(current_value))
        if values:
            results_sheet.cell(row=32, column=column, value=sum(values)/len(values))
        else:
            results_sheet.cell(row=32, column=column, value=0)

    results_sheet.cell(row=35, column=2, value=sum([results_sheet['B32'].value, results_sheet['D32'].value, results_sheet['F32'].value]))
    results_sheet.cell(row=35, column=3, value=sum([results_sheet['C32'].value, results_sheet['E32'].value, results_sheet['G32'].value])/3.0)
    results_sheet.cell(row=35, column=4, value=sum([results_sheet['H32'].value, results_sheet['I32'].value, results_sheet['J32'].value, results_sheet['K32'].value]))

    results.save(filename)

dict = {'false_0_roundRobin':2, 'false_1_roundRobin':5,
        'false_2_roundRobin':8, 'false_3_roundRobin':11,
        'false_2_random':14, 'false_3_random':17,
        'false_2_leastBandwidth':20, 'false_3_leastBandwidth':23,
        'true_0_roundRobin':26, 'true_1_roundRobin':29,
        'true_2_roundRobin':32, 'true_3_roundRobin':35,
        'true_2_random':38, 'true_3_random':41,
        'true_2_leastBandwidth':44, 'true_3_leastBandwidth':47}

main_filename = "Magisterka_dane.xlsx"
main_wb = load_workbook(main_filename)
main_sheet = main_wb["Results"]

for pattern in dict:
    files = fnmatch.filter(os.listdir('.'), '*'+pattern+'*xlsx')
    for filename in files:
        num = int(re.findall(r"(\d+).xlsx", filename)[0])
        results_wb = load_workbook(filename)
        results_wb = load_workbook(filename, data_only=True, read_only=True)
        results_sheet = results_wb.active

        a = results_sheet.cell(row=35, column=2).value
        b = results_sheet.cell(row=35, column=3).value
        c = results_sheet.cell(row=35, column=4).value
    
        main_sheet.cell(row=2+num, column=dict[pattern], value=a)
        main_sheet.cell(row=2+num, column=dict[pattern]+1, value=b)
        main_sheet.cell(row=2+num, column=dict[pattern]+2, value=c)
        results_wb.close()
    
main_wb.save(main_filename)
print("*** DONE ***")


