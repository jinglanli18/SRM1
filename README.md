# SRM1
Implementation of the main part of SRM1.
## Introduction
After the synthesis project, the classification of the four road types has been successfully carried out. The next step is to implement the SRM1 model so that for a given location, the air quality of it can be automatically calculated. There is an example use of this program inside the script.
## Environment
* Python 3.7
* pandas 0.24.2
* fiona 1.8.4
* shapely 1.6.4.post1
## Use
Simply import it and call the function with required inputs:
```
import SRM1
roadFile = 'road_demo.shp'
excelFile = 'CAR VL3.0, v3_English_Belgium.xlsx'
x = 126362
y = 181317
print("{}: {}".format("NO2", concentration(roadFile, excelFile, x, y, 'NO2')))
```
There are four mandatory parameters as inputs:
1. 2D coordinates of a location in Belge 1972 (EPSG: 31370).
2. Road file in `.shp` format. For a single road geometry, eight fields must be available:
  * *class*: a character indicating road type. Available values are '1', '2', '3', and '4'.
  * *intensity*: the number of vehicles per day.
  * *speed_type*: the type of the travel speed of vehicles on this road when there is no congestion. Available values are 'a'(100km/h), 'b'(44km/h), 'c'(19km/h), 'd'(13km/h), and 'e'(26km/h).
  * *f_cong*: a number between 0 and 1 indicating the possibility of congestion.
  * *f_medium*: a number between 0 and 1 indicating the proportion of medium-weight vehicles.
  * *f_heavy*: a number between 0 and 1 indicating the proportion of heavy vehicles.
  * *f_bus*: a number between 0 and 1 indicating the proportion of buses.
  * *t_factor*: a number indicating the presence of trees. Available values are 1, 1.25, 1.5.
3. Excel file 'CAR VL3.0, v3_English_Belgium.xlsx'. Providing the program with background concentrations, emission factors, and wind speeds. You can find it in this repository.
4. Pollutant. Available values are 'NO2', 'PM10', 'PM25', and 'EC'. 'Benzene' not supported yet.
## Status
1. As mentioned above, the CRS is Belge 1972. So this program isn't applicable for loactions in Netherlands now.
2. This program supports the calculation of annual average concentration of NO2, PM10, PM2.5, and EC. Benzene is not supported yet because the calculation of its emission number hasn't been implemented. The following calculations are not supported yet either:
* the number of times per year that the twenty-four-hour average concentration of suspended particles (PM10) is higher than the limit value of 50 μg / m3;
* the 98 percentile of the eight-hour average concentration of carbon monoxide;
* the number of times per year that the twenty-four-hour average concentration of sulfur dioxide is higher than the limit value of 125 μg / m3;
* the number of times per year that the hourly average concentration of nitrogen dioxide is higher than the limit value of 200 μg / m3.
