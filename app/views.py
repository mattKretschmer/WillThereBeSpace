from flask import render_template,request
from app import app
import pymysql as mdb
import numpy as np
from scipy.spatial import KDTree
from datetime import datetime
from pytz import timezone
from a_Model import *


#@app.route('/input')
@app.route('/') 
def station_input():
	'''Renders the landing page'''
	return render_template("input.html")

@app.errorhandler(IndexError)
def bad_value(e):
	'''Renders a page if there's an error in any of the user inputs'''
	return render_template('bad_dest_err.html')
	
@app.route('/output')
def station_output():
	#pull 'Id' from input field and how long the forecast will be.
	station_id = request.args.get('Id')
	arrival_t = request.args.get('Arrival_Time')

	#Set default values if none entered by user, geocode station_id
	station_id, arrival_t = set_Default(station_id,arrival_t)
	
	#Connect to the Citi Bike Stations data base.
	db = mdb.connect(user="root",host = "localhost",passwd="",db = "Citibike_Stations",charset='utf8')
	arr = request.args.get('Status')
	with db:
		cur = db.cursor()
		cur.execute("USE Citibike_Stations;")
		cur.execute("SELECT Latitude,Longitude FROM Station_LatLongs ;")
		station_points = cur.fetchall() #station_points is now a tuple of tuples, holding all of the station information	
	cur.close()
	station_tree = KDTree(station_points)
	#Find index of nearest 2 stations station, now nn and nnn will hold tuples of lat long coordinates for both of these
	dists,inds = find_nearest_station(station_tree,station_id)
	nn = station_points[inds[0]]#Closest to address (lat,longs)
	nnn = station_points[inds[1]]#Next Nearest Neighbor	
	
	with db:
		cur = db.cursor()
		#Select the station_id from the Citibike_Stations that the user inputs
		cur.execute("SELECT Id,Latitude,Longitude,streetAddress FROM Station_LatLongs WHERE Latitude = {} AND Longitude={};".format(nn[0],nn[1]))
		querynn_results = cur.fetchall()
		cur.execute("SELECT Id,Latitude,Longitude,streetAddress FROM Station_LatLongs WHERE Latitude = {} AND Longitude={};".format(nnn[0],nnn[1]))
		querynnn_results = cur.fetchall()
	cur.close()
	
	t_list = find_times(arrival_t) #Find current time window, time window when arriving at station.
	#Holds id, lat/long and address of closest stations to input address.
	stats = []
	stats.append(dict(Id=querynn_results[0][0],Latitude = querynn_results[0][1],Longitude=querynn_results[0][2],streetAddress = querynn_results[0][3]))
	stats.append(dict(Id=querynnn_results[0][0],Latitude = querynnn_results[0][1],Longitude=querynnn_results[0][2],streetAddress = querynnn_results[0][3]))
	
	point = (stats[0]['Latitude'],stats[0]['Longitude'])
	nn_id = str(stats[0]['Id'])
	nnn_id = str(stats[1]['Id'])
	
	#Assumes that the data is in the current directory, would need to change if that was not the case!
	data_path = ''
	dicta = get_data_dict(data_path,nn_id)
	dictb = get_data_dict(data_path,nnn_id)
	num_of_values = 1000
	
	trip_valuesa = integrate_fluxes(np.zeros(num_of_values),dicta,num_of_values,t_list)
	trip_valuesb = integrate_fluxes(np.zeros(num_of_values),dictb,num_of_values,t_list)

	#Find total available slots, and address of nearest and next-nearest neighbor stations
	sl = get_total_slots(nn_id)#Returns a dict with 'open' and 'total' , and address
	nnsl = get_total_slots(nnn_id)
	nnsl['Longitude'] = stats[1]['Longitude']
	nnsl['Latitude'] = stats[1]['Latitude']
	stats[0]['Arrival_Time'] = arrival_t
	stats[0]['Delta_B'] = mode(trip_valuesa)
	stats[1]['Delta_B'] = mode(trip_valuesb)
	
	if arr == 'Leaving':
		#Arriving at the station, looking for a bike, find out probability of no bikes by the time you get there, and render the template.
		prob_a = find_probability(trip_valuesa,sl['open']-sl['total'])
		prob_b = find_probability(trip_valuesb,nnsl['open']-nnsl['total'])
		stats[0]['P_0'] = int(prob_a*100.0)
		stats[1]['P_0'] = int(prob_b*100.0)
		
		stats = realistic_Delta_Bike(stats,sl['total'] - sl['open'],nnsl['total'] - nnsl['open'])
		sl['open'] = sl['total'] - sl['open']
		nnsl['open'] = nnsl['total'] - nnsl['open']
		return render_template("leaving_output.html",stats = stats,sl = sl,nsl = nnsl)
	else:
		#Arriving at the station (with a bike), looking for a spot, find probability of too many bikes.
		prob_a = find_probability(trip_valuesa,sl['open'])
		prob_b = find_probability(trip_valuesb,nnsl['open'])
		stats[0]['P_0'] = (1. - prob_a)*100.0
		stats[1]['P_0'] = (1. - prob_b)*100.0
		
		stats = realistic_Delta_Slots(stats,sl['open'],nnsl['open'])
		return render_template("output.html",stats = stats,sl = sl,nsl = nnsl)
