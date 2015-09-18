#!/usr/local/bin/python
import os
from datetime import datetime
import pandas as pd
import numpy as np
import time
import cPickle as pickle
from scipy.stats import itemfreq

'''A script to process the raw bike data, held in files ending with "tripdata.csv". Writes to a file all of the rides that occurred on weekdays in the "summer months", from May to August. The later part of the script finds the distribution of bike changes at each station for every 5 minute interval throughout a weekday, and pickles the result.'''


#Find the names of all files in the current directory holding Citi Bike trip data.

files = []
for file in os.listdir("."):
	if file.endswith("tripdata.csv"):
		files.append(file)
		
new_path = "summer_weekday_trips_data-5678.csv"
summer_months = [5,6,7,8]
weekends = [5,6]
f = open(new_path,'w')
for file in files:
	with open(file) as infile:
		infile.readline()
		for line in infile:
			a = line.replace('/','-')
			split_line = a.replace('\"','').split(',')
			now_string = split_line[1]
			to_write = split_line[:-3]
			try:
				now = datetime.strptime(now_string,"%Y-%m-%d %H:%M:%S")
			except ValueError:
				continue
			if now.month == 7 and now.weekday() == 4:
				continue

			if now.month in summer_months and now.weekday() not in weekends:
				to_write.append(str(now.weekday()))
				line_to_write = ','.join(to_write)
				f.write(line)
			else:
				continue
 
f.close()


#Station_Ids.csv holds the ids used to index all of the Citi Bike stations throughout NYC.

stations = []
f = open('Station_Ids.csv')
for line in f:
	stations.append(line.replace('\n',''))
f.close()

f = open('summer_weekday_trips_data-5678.csv','r')
s = set([])
# Collect the dates that rides occur, and store in the set "s"
for line in f:
    s_l = line.replace('\"','').split(',')
    if s_l[1][0:10] == s_l[2][0:10]:
    	to_add = s_l[1][0:10]
    	if to_add not in s:
        	s.add(to_add)
f.close()
dates = list(s)


dt_intervals = 288 # There are 288 5 minute intervals in a day
delta_t = 300 # Times between rides are in seconds, 300s = 5min
dates.sort()



# Now, we breakdown the trips and save the distribution of trips for each station. Will loop through all trips for each station. Very inefficient, but only happens once, offline.
for station in stations:
	net_trips = pd.DataFrame(0,index = dates,columns = np.arange(dt_intervals))
	with open("summer_weekday_trips_data-5678.csv") as infile:
		for line in infile:
			split_line = line.replace('\"','').split(',')
			
			#Makes sure that we're only calculating statistics for the station we care about
			if split_line[3] != station and split_line[7] != station:
				continue
			out_day = split_line[1][0:10]
			in_day = split_line[2][0:10]
			if out_day != in_day:
				continue
				
			#'''Find dt interval'''
			in_ts = split_line[2]
			out_ts = split_line[1]
			earlier_ints = in_day + ' 00:00:00'
			earlier_outts = out_day + ' 00:00:00'
			
			out_now = datetime.strptime(out_ts,"%Y-%m-%d %H:%M:%S")
			in_later = datetime.strptime(in_ts,"%Y-%m-%d %H:%M:%S")
			out_mid = datetime.strptime(earlier_outts,"%Y-%m-%d %H:%M:%S")
			in_mid = datetime.strptime(earlier_ints,"%Y-%m-%d %H:%M:%S")
			t_out = int((out_now-out_mid).total_seconds()/delta_t) # When was the bike taken
			t_in = int((in_later-in_mid).total_seconds()/delta_t)#When did the bike get returned
			
			if split_line[7] == station:
				net_trips.loc[in_day,t_in] += 1
			if split_line[3] == station:
				net_trips.loc[out_day,t_out] -= 1
				
	##Now that data has been processed, so only the net bike change of a given station is stored, record (discrete) distribution of bike changes for each time window over the course of the day. pk will be the probability of a change of magnitude xk. 
	station_dict = {}
	for i in range(dt_intervals):
		station_dict[i] = []
		a = itemfreq(net_trips.loc[:,i])
		length = 1.0*len(net_trips.loc[:,i])
		xk = a[:,0] 
		pk = a[:,1]/length
		station_dict[i].append(pk)
		station_dict[i].append(xk)
	# Save (pickle) the distributions, to be loaded at later time, when necessary
	save_path = station + 'data.p'
	pickle.dump( station_dict, open( save_path, "wb" ) )
