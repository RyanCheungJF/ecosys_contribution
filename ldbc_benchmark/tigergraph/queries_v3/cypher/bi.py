#!/usr/bin/env python3
from neo4j import GraphDatabase, time
from datetime import datetime
from neo4j.time import DateTime, Date
import time
import pytz
import csv
import re
import ast
import os
from pathlib import Path

#@unit_of_work(timeout=300)
def query_fun(tx, query_spec, query_parameters):
    result = tx.run(query_spec, query_parameters)
    values = []
    for record in result:
        values.append(record.values())
    return values

result_dir = Path('results') 
time_dir = Path('elapsed_time')
result_dir.mkdir(parents=True, exist_ok=True)
time_dir.mkdir(parents=True, exist_ok=True)

def writeResult(result, filename):
    with open(filename, 'w') as f:
        for row in result:
            # convert neo4j dateTime to string
            for i,c in enumerate(row):
                if isinstance(c, DateTime): 
                    row[i] = f"{c.year}-{c.month:02d}-{c.day:02d} {int(c.hour):02d}:{int(c.minute):02d}:{int(c.second):02d}"
            f.write(str(row)+'\n')

def run_query(session, query_id, query_spec, query_parameters):
    #print(f'Q{query_id}: {query_parameters}')
    start = time.time()
    result = session.read_transaction(query_fun, query_spec, query_parameters)
    end = time.time()
    duration = end - start
    print("BI{}: {:.4f} seconds, {} results".format(query_id, duration, len(result)))
    writeResult(result, result_dir / f'bi{query_id}.txt')
    with open(time_dir / f'bi{query_id}.txt', 'w') as f:
        f.write(str(duration))
    
def convert_to_datetime(timestamp):
    dt = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
    return DateTime(dt.year, dt.month, dt.day, 0, 0, 0, pytz.timezone('GMT'))

def convert_to_date(timestamp):
    dt = datetime.strptime(timestamp, '%Y-%m-%d')
    return Date(dt.year, dt.month, dt.day)

def readJson(paramFile):
    with open(paramFile) as f: 
        txt = f.read().replace('\n','')
        return ast.literal_eval(txt)
driver = GraphDatabase.driver("bolt://localhost:7687")



# read parameters
allParameters = readJson('../parameters/sf1.json')
dataType = readJson('../parameters/dataType.json')
# replace the date in bi1 to datetime
allParameters['bi1'] = {'datetime':allParameters['bi1']['date']}
def convert(k,v):
    if dataType[k] in ["ID", "LONG"]:
        return int(v)
    if dataType[k] == "DATE":
        return convert_to_date(v)
    if dataType[k] == "DATETIME":
        return convert_to_datetime(v)
    if dataType[k] == "STRING":
        return v
    if dataType[k] == "STRING[]":
        return v.split(';')
    else:
        raise Exception(f'Error: Datatype of {k}:{v} is unknown.')
for query, parameters in allParameters.items():
    allParameters[query] = {k: convert(k,v) for k, v in parameters.items()}

with driver.session() as session:
    for query_variant in ["4"]: #["1", "2", "3", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"]:
        query_num = re.sub("[^0-9]", "", query_variant)
        query_file = open(f'queries/bi-{query_variant}.cypher', 'r')
        query_spec = query_file.read()
        run_query(session, query_variant, query_spec, allParameters['bi'+str(query_variant)])
            

driver.close()