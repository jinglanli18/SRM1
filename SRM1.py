# -*- coding: utf-8 -*-
"""
Created on Sat Aug 17 21:41:50 2019

@author: Jinglan Li

Note: Concentration calculation for NO2, PM10, PM25, EC. Benzene not supported yet.
"""
import fiona
import pandas as pd
from shapely.geometry import Point, shape



def concentration(rFile, eFile, x, y, pollutant):
    """
    Calculate the concentration of the input pollutant at point (x, y).
    Input:
        rFile: road file. Necessary properties: class, intensity, f_cong, f_medium, f_heavy, f_bus, speed_type, t_factor
        eFile: template excel file.
        x, y: coordinates of the calculation point
        pollutant: NO2, PM10, PM25, EC. (Benzene not supported yet)
    """
    sheets = pd.read_excel(eFile, sheet_name = None)
    if pollutant in ['NO2', 'PM10', 'PM25', 'EC']:
        c_traffic = traffic_concentration(rFile, sheets, x, y, pollutant)
        if c_traffic == 'e1':
            print("The calculation point is more than 60 meters far away from the street.")
            return None
        c_background = background_concentration(sheets, x, y, pollutant)
#        print(c_traffic, c_background)
        return round(c_traffic + c_background, 1)
    else:
        print("Pollutant {} is not supported yet.".format(pollutant))
        return None

def nearest_road(p, file):
    """
    Given a point p, find the nearest road that p belongs to.
    Return the road type and the distance from p to this road.
    """
    with fiona.open(roadFile, 'r') as roads:
        nearestRoad = roads[0]
        minDis = p.distance(shape(roads[0]['geometry']))
        for road in roads:
            dis = p.distance(shape(road['geometry']))
            if dis < minDis:
                nearestRoad = road
                minDis = dis
    return nearestRoad, minDis

def traffic_concentration(rFile, sheets, x, y, pollutant):
    """
    Calculate the traffic concentration at the point (x, y).
    """
    p = Point(x, y)
    road, dis = nearest_road(p, rFile)
    
    # step 1. check whether this location is within the calculation range. If so, go on. Otherwise exit.
    if dis > 60: # I think we dont have to consider points that are too far from the streets.
        return 'e1' # error 1
    
    if dis < 3.5:
        dis = 3.5 # In the NSL calculation tool, calculation distance smaller than 3.5 meters are limited to 3.5 meters.
    
    # step 2. determine all the parameters required.
    
    #calibration factor
    Fk = 0.62
    
    # Emission number. for SO2, NO2, NOx, PM10, PM2.5, lead, and CO
    N = int(road['properties']['intensity']) #the traffic intensity, being the number of vehicles per day
    Fs = float(road['properties']['f_cong']) #fraction of stagnant traffic, a number between 0 and 1
    Fm = float(road['properties']['f_medium']) #fraction of medium-weight motor vehicles
    Fz = float(road['properties']['f_heavy']) #fraction of heavy motor vehicles
    Fb = float(road['properties']['f_bus']) #fraction of buses
    st = str(road['properties']['speed_type']) #intotal 5 types: a:100, b:44, c:19, d:13, e:26 (km/h)
    El = emission_factor(sheets, 'p', st, pollutant) #emission factor of light motor vehicles
    Em = emission_factor(sheets, 'm', st, pollutant) #emission factor of medium-weight motor vehicles
    Ez = emission_factor(sheets, 'v', st, pollutant) #emission factor of heavy motor vehicles
    Eb = emission_factor(sheets, 'b', st, pollutant) #emission factor of buses
    Eld = emission_factor(sheets, 'p', 'd', pollutant) #emission factor of light motor vehicles (speedType: d)
    Emd = emission_factor(sheets, 'm', 'd', pollutant) #emission factor of medium-weight motor vehicles (speedType: d)
    Ezd = emission_factor(sheets, 'v', 'd', pollutant) #emission factor of heavy motor vehicles (speedType: d)
    Ebd = emission_factor(sheets, 'b', 'd', pollutant) #emission factor of buses (speedType: d)
    
    E_regular = N * (1 - Fs) * ((1 - Fm - Fz - Fb) * El + Fm * Em + Fz * Ez + Fb * Eb) * 1000 / 24 / 3600
    E_cong = N * Fs * ((1 - Fm - Fz - Fb) * Eld + Fm * Emd + Fz * Ezd + Fb * Ebd) * 1000 / 24 / 3600
    E = E_regular + E_cong
#    print("{}: {}, {}".format(pollutant, E_regular, E_cong))
    #dilution factor
    roadType = str(road['properties']['class'])
    if roadType == '1': # Broad street canyon
        a = 0.000325
        b = -0.0205
        c = 0.39
        alpha = 0.856
    elif roadType == '2': # Small street canyon
        a = 0.000488
        b = -0.0308
        c = 0.59
        alpha = None
    elif roadType == '3': # One-sided buildings
        a = 0.0005
        b = -0.0316
        c = 0.57
        alpha = None
    elif roadType == '4': # General urban
        a = 0.000310
        b = -0.0182
        c = 0.33
        alpha = 0.799
    
    if dis > 30 and (roadType == 1 or roadType == 4):
        theta = alpha * pow(dis, -0.747)
    else:
        theta = a * dis**2 + b * dis + c
        
    #tree factor
    Fb = road['properties']['t_factor']
    
    #wind speed
    ws = wind_speed(sheets, x, y) # average speed from CAR VL3.0
    
    #regional factor related to meteorology
    Fregio = 5 / ws
    
    # step 3. calculate the traffic concentration based on the parameters above.
    C_traffic = Fk * E * theta * Fb * Fregio
    
    # If it is NO2, then NOx has to be considered due to its chemical reaction with O3.
    if pollutant == 'NO2':
        B = 0.6 # fixed number?
        K = 100 # parameter for the conversion from NO to NO2
        C_background_O3 = background_concentration(sheets, x, y, 'O3')
        C_traffic_NOx = traffic_concentration(rFile, sheets, x, y, 'NOx')
        C_traffic = C_traffic + B * C_background_O3 * (C_traffic_NOx - C_traffic) / (C_traffic_NOx - C_traffic + K)
        
    return C_traffic


def background_concentration(sheets, x, y, pollutant):
    """
    Get the background concentration value at point (x, y) from the template file.
    Available pollutant: NO2, O3, PM10, PM25, EC
    """
    i, j = coor2idx(x, y)
        
    # get bc from excel. The year is hard coded to 2015
    f = sheets["Backgroundconc"]
    idx = f[f['XiYI'] == str(i) + "-" + str(j)].index
    if len(idx) == 0:
        print("BCError: No location found. 0 returned.")
        return 0
    return float(f[pollutant+'_2015'][idx])



def emission_factor(sheets, vehicleClass, speedRegime, pollutant):
    """
    Get the emission factors at point (x, y) from file.
    Available pollutant: NOx, NO2, O3, PM10, PM2.5, EC
    """
    # get bc from excel. The year is hard coded to 2015
    f = sheets["Emissiefactoren CAR-VL3.0"]
    idx = f[f.iloc[:,0] == vehicleClass + speedRegime + '2015'].index
    if len(idx) == 0:
        print("EFError: No ef corresponds to vehicle class {} and speed type {}.".format(vehicleClass, speedRegime))
        return 0
    return float(f['EF_' + pollutant][idx])
    
    
def wind_speed(sheets, x, y):
    """
    get wind speed at point (x, y) from excel.
    """
    i, j = coor2idx(x, y)
        
    # get ws from excel. The year is hard coded to 2012
    f = sheets["Meteo CAR-VL3.0"]
    idx = f[f['Search key'] == int(str(i) + str(j) + "2012")].index
    if len(idx) == 0:
        print("WSError: No location found.")
        return 0
    return float(f['Windspeed'][idx])

def coor2idx(x, y):
    """
    Translate coordinates into indices (as being used in CAR VL3.0).
    In fact, I dont know in which CRS the coordinates are. I just followed what has been done in excel.
    """
    a = round(x/4000,0)*4000
    b = (round_down(y/4000,0)+0.5)*4000
    i = int((a - 24000)/4000) + 1
    j = int((b - 22000)/4000) + 1
    return i, j

def round_down(n, decimals=0):
    """
    Round a number to n decimal places (same as 'rounddown' in excel).
    """
    multiplier = 10 ** decimals
    return int(n * multiplier) / multiplier

# Example use:
if __name__ == '__main__':
    roadFile = 'road_demo.shp'
    excelFile = 'CAR VL3.0, v3_English_Belgium.xlsx'
    # Dirk Martensstraat, Aalst 
    x = 126362
    y = 181317
#    print( nearest_road(Point(x, y), roadFile))
    print("Air quality at position ({}, {}):".format(x, y))
    print("\n{:10} {} {:13}".format("Pollutant", "|", "Concentration"))
    print("-"*25)
    print("{:10} {} {:13}".format("NO2", "|", concentration(roadFile, excelFile, x, y, 'NO2')))
    print("{:10} {} {:13}".format("PM10", "|", concentration(roadFile, excelFile, x, y, 'PM10')))
    print("{:10} {} {:13}".format("PM25", "|", concentration(roadFile, excelFile, x, y, 'PM25')))
    print("{:10} {} {:13}".format("EC", "|", concentration(roadFile, excelFile, x, y, 'EC')))






