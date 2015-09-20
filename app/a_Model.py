#!/usr/local/bin/python
from scipy.stats import rv_discrete,itemfreq
import numpy as np
import cPickle as pickle
import time
import requests
from scipy.spatial import KDTree
from geopy import geocoders
from pytz import timezone
from datetime import datetime


def set_Default(station_id,arrival_t):
	if station_id == '':
		station_id = '45 W 25th Street, New York, NY'
	if arrival_t == '':
		arrival_t = 20
	return station_id,arrival_t

def get_total_slots(station_id):
	"""Finds the number of slots currently available at a bike station indexed by station_id, by querying the Citi Bike API"""
	api_address = 'http://www.citibikenyc.com/stations/json'
	request = requests.get(url = api_address)
	station_dict = request.json()
	stations = station_dict['stationBeanList']
	for station in stations:
		if str(station['id']) == station_id:
			r_t = {'open':station['availableDocks'],'total':(station['availableBikes']+station['availableDocks']),'streetAddress':station['stAddress1']}
	return r_t

def find_nearest_station(tree,point):
	distance,index = tree.query(point,2,p=2)
	return distance,index


def get_data_dict(data_path,nn_id):
	return pickle.load(open(data_path+nn_id+'data.p','rb'))

def arriving_Verb(stats,index):
	'''Determines which verb to render in html, depending on whether the station will have spaces (be open) or not (be closed)'''
	if stats[index]['Delta_B'] < 0:
		stats[index]['verb'] = 'open'
	else:
		stats[index]['verb'] = 'close'
	return stats
	
def leaving_Verb(stats,index):	
	p_verb = 'appear'
	n_verb = 'disappear'
	if stats[0]['Delta_B'] <= 0:
		stats[0]['verb'] = n_verb
	else:
		stats[0]['verb'] = p_verb
	return stats

def integrate_fluxes(trip_values,dicta,num_of_values,t_list):
	'''Finds array of possible net bike changes over the next time periods'''
	for t in t_list:
		pk = dicta[t][0]
		xk = dicta[t][1]
		trip_values += discrete_probs(xk,pk,num_of_values)
	return trip_values

def discrete_probs(xk,pk,num_of_values):
	'''Returns an array of values generated from the discrete distribution characterized by xk and pk.'''
	distrib = rv_discrete(values = (xk,pk))
	return distrib.rvs(size = num_of_values)

def find_probability(trip_holder,bikes_left):
	'''Calculate the probabilty of the bike change being less than the number of bikes left'''
	xk,pk = get_counts(trip_holder)
	ndb = rv_discrete(values = (xk,pk))
	return ndb.cdf(bikes_left)

def realistic_Delta_Bike(stats,limit1,limit2):
	stats = leaving_Verb(stats,0)
	stats = leaving_Verb(stats,1)
		
	if stats[0]['Delta_B'] < -limit1:
		stats[0]['Delta_B'] = -limit1
	if stats[1]['Delta_B'] < -limit2:
		stats[1]['Delta_B'] = -limit2	
	
	stats[0]['Delta_B'] = abs(stats[0]['Delta_B'])
	stats[1]['Delta_B'] = abs(stats[1]['Delta_B'])	
	return stats

def realistic_Delta_Slots(stats,limit1,limit2):
	stats = arriving_Verb(stats,0)
	stats = arriving_Verb(stats,1)
	if stats[0]['Delta_B'] > limit1:
		stats[0]['Delta_B'] = limit1
	if stats[1]['Delta_B'] > limit2:
		stats[1]['Delta_B'] = limit2
	stats[0]['Delta_B'] = abs(stats[0]['Delta_B'])
	stats[1]['Delta_B'] = abs(stats[1]['Delta_B'])	
	return stats
	
def find_time(arrival_t):
	#Calculate (from computer time, when inquiry is made, and when station will be arrived at.
	now_time = datetime.now(timezone('US/Eastern'))
	t = now_time.strftime("%H:%M:%S")

	#ct is the current time, in seconds, from midnight of that day
	ct = 3600*int(t[0:2])
	ct += (60*int(t[3:5]))
	ct += int(t[6:])
	end_time = ct + 60*int(arrival_t)
	#Times had been in seconds, divide by 300 to find time index of 5 minute block.
	ct /= 300
	end_time /= 300
	return end_time,ct

def get_counts(data):
	a = itemfreq(data)
	length = 1.0*len(data)
	return a[:,0],a[:,1]/length

def mode(a, axis=0):
	"""Find mode of values in array a"""
	scores = np.unique(np.ravel(a))# get ALL unique values
	testshape = list(a.shape)
	testshape[axis] = 1
	oldmostfreq = np.zeros(testshape)
	oldcounts = np.zeros(testshape)
	for score in scores:
		template = (a == score)
		counts = np.expand_dims(np.sum(template, axis),axis)
		mostfrequent = np.where(counts > oldcounts, score, oldmostfreq)
		oldcounts = np.maximum(counts, oldcounts)
		oldmostfreq = mostfrequent
	return int(mostfrequent[0])