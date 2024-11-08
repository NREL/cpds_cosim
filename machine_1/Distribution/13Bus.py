# -*- coding: utf-8 -*-
"""
feeder simulator
author: Wenbo.Wang@nrel.gov
"""

from datetime import datetime
import cmath
import json
import math
import re
import os
import sys
import numpy as np
from pathlib import Path

import helics as h
import opendssdirect as dss
from opendssdirect.utils import run_command

import csv
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

def config_file(path: str) -> str:
    if os.path.exists(path):
        return path

    raise ValueError("File '" + path + "' does not exist")

def positive_value(value: str) -> float:
    val = float(value)
    if val > 0:
        return val
    raise ValueError("Value must be positive")

# run_time = 5.0

mydir = Path(os.path.dirname(__file__))


# filename = mydir/"test.json"
# with open(filename) as f:
#     data = json.loads(f.read())
#     federate_name = data["name"]
#     total_time = data["total_time"]
#     simulation_step_time = data["simulation_step_time"]
#     subscriptions = data["subscriptions"]
#     publications = data["publications"]
# print("reading json okay!")

#fedinitstring = "--federates=1"
fedinitstring = '--federates=1 --broker_address=<IP>:<port number>' 
deltat = 0.01

helicsversion = h.helicsGetVersion()

print("Helics version = {}".format(helicsversion))

# Create Federate Info object that describes the federate properties */
print("OPENDSS_DIS: Creating Federate Info")
fedinfo = h.helicsCreateFederateInfo()

# Set Federate name
print("OPENDSS_DIS: Setting Federate Info Name")
federate_name = '13Bus'
h.helicsFederateInfoSetCoreName(fedinfo, federate_name)

# Set core type from string
#print("PI RECEIVER: Setting Federate Info Core Type")
h.helicsFederateInfoSetCoreTypeFromString(fedinfo, "tcp_ss")

# Federate init string
#print("PI RECEIVER: Setting Federate Info Init String")
h.helicsFederateInfoSetCoreInitString(fedinfo, fedinitstring)

# Set the message interval (timedelta) for federate. Note that
# HELICS minimum message time interval is 1 ns and by default
# it uses a time delta of 1 second. What is provided to the
# setTimedelta routine is a multiplier for the default timedelta.

# Set one second message interval
print("OPENDSS_DIS: Setting Federate Info Time Delta")
h.helicsFederateInfoSetTimeProperty(fedinfo, h.helics_property_time_delta, deltat)

# Create value federate
#print("OPENDSS_DIS: Creating Value Federate")
fed = h.helicsCreateCombinationFederate(federate_name, fedinfo)
print("OPENDSS_DIS: Value federate created")

PUBLICATIONS = {}
SUBSCRIPTIONS = {}




# register publication
pub = h.helicsFederateRegisterGlobalTypePublication(fed, "13Bus/Totalpower", "double", "")
PUBLICATIONS['psse'] = pub


# register publication
pub = h.helicsFederateRegisterGlobalTypePublication(fed, "13Bus/DER_node_voltage", "double", "")
PUBLICATIONS['pscad'] = pub

pub = h.helicsFederateRegisterGlobalTypePublication(fed, "13Bus/current_frequency", "double", "")
PUBLICATIONS['pscad_frequency'] = pub

print("OPENDSS_DIS: Publication registered")

# Subscribe to PI SENDER's publication
sub = h.helicsFederateRegisterSubscription(fed, "DER/power_p", "")
SUBSCRIPTIONS['pscad_p'] = sub

sub = h.helicsFederateRegisterSubscription(fed, "DER/power_q", "")
SUBSCRIPTIONS['pscad_q'] = sub

sub = h.helicsFederateRegisterSubscription(fed, "transmission/bus11/voltage", "")
SUBSCRIPTIONS['psse'] = sub

sub = h.helicsFederateRegisterSubscription(fed, "transmission/bus11/frequency", "")
SUBSCRIPTIONS['psse_frequnecy'] = sub

print("OPENDSS_DIS: Subscription registered")

# Subscribe to PI SENDER's publication
#sub = h.helicsFederateRegisterSubscription(vfed, "power_pscad", "")
print("OPENDSS_DIS: Subscription registered")

h.helicsFederateEnterExecutingMode(fed)
print("OPENDSS_DIS: Entering execution mode")

value = 0.0



reply = dss.run_command("redirect ./13Bus/IEEE13Nodeckt.dss")
if reply == "":
    print('opendss test run okay')
else:
    print('opendss test not okay')

current_time = 0

total_time = 3
simulation_step_time = 0.02
time_array = np.arange(0, total_time, simulation_step_time)

# Generate random numbers for each time step

np.random.seed(42)
random_numbers = np.random.uniform(low=0.9, high=1.1, size=time_array.size)
# random_numbers[4] = 2
# random_numbers[5] = 2

n=0

v_list = []
current_time_list = []
event_time = 2

for request_time in np.arange(0 ,total_time, simulation_step_time):

    while current_time < request_time:
        current_time = h.helicsFederateRequestTime(fed, request_time)
    current_time_list.append(current_time)
    print(f'=== time step = {current_time} seconds ===')


    
    

    
    
    # Vvalue = dss.Circuit.AllBusMagPu()[-1]
    # val = Vvalue
    # print(f'Output voltage example = {val}')
    

    # loadname = '671'
    # kw = -float(value)*1000 # convert to kw from mw
    
    # if current_time< 1-simulation_step_time:
    #     kw = 0
    #     print(f'Discard received value, use kw={kw}')
    # dss.run_command(f'edit load.{loadname} kw={kw}')
    for key, sub in SUBSCRIPTIONS.items():
        if key == 'psse':
            val = h.helicsInputGetVector(sub)
       

            print(f"Received voltage mag and angel_deg at time {current_time}: {val} pu")
  
            # change the substation voltage and angle based on sub
            if current_time <1:
                print('manually set up first step voltage')
                voltage = 1
                angle_deg = 0
            else:
                voltage = val[0]
                #angle_deg = val[1]
            #dss.Vsources.AngleDeg(angle_deg)
            dss.Vsources.PU(voltage)
            #dss.run_command(f'set loadmult={random_numbers[n]}')
            v_list.append(voltage)
            #n+=1

        if key == 'psse_frequnecy':
            val = h.helicsInputGetDouble(sub)
            current_frequency = val

            print(f"Received frequency at time {current_time}: {val} Hz")
  

        if key == 'pscad_p':
            value = h.helicsInputGetString(sub)
            print(
                "OPENDSS_DIS: Received Power = {} mw at time {} from PSCAD_DER".format(
                    value, current_time
                )
            )    
            loadname = '671'
            kw = -float(value)*1000 # convert to kw from mw
            #time.sleep(1)
            if current_time< simulation_step_time:
                kw = 0
                print(f'Discard received value, use kw={kw}')
            dss.run_command(f'edit load.{loadname} kw={kw}')
        if key == 'pscad_q':
            value = h.helicsInputGetString(sub)
            print(
                "OPENDSS_DIS: Received Power_q = {} mvar at time {} from PSCAD_DER".format(
                    value, current_time
                )
            )    
            # loadname = '671'
            # kw = -float(value)*1000 # convert to kw from mw
            # #time.sleep(1)
            if current_time< simulation_step_time:
                kvar = 0
                #print(f'Discard received value, use kw={kw}')
    
    reply = dss.run_command("solve")
    if reply == "":
        print(f'Opendss run okay at time {current_time} !')
    else:
        print(f'opendss not okay at time {current_time} !')

    S = dss.Circuit.TotalPower() # the total power from opendss is negative
    val = -S[0]



    for key, pub in PUBLICATIONS.items():
        if key == 'psse':
    
            h.helicsPublicationPublishDouble(pub, val)
            print(f"Sending active power = {val} at time {current_time} to Transmission")
        if key == 'pscad':
            Vvalue = dss.Circuit.AllBusMagPu()[-1]
            val = Vvalue
            #print(f'Output voltage example = {val}')
            h.helicsPublicationPublishDouble(pub, val)
            print(f"Sending voltage = {val} at time {current_time} to PSCAD_DER")

        if key == 'pscad_frequency':
            #Vvalue = dss.Circuit.AllBusMagPu()[-1]
            val = current_frequency
            #print(f'Output voltage example = {val}')
            h.helicsPublicationPublishDouble(pub, val)
            print(f"Sending frequency = {val} Hz at time {current_time} to PSCAD_DER")


os.chdir(mydir)        

df = pd.DataFrame()
df['current_time'] = current_time_list
df['feeder_head_voltage'] = v_list
df.to_csv(mydir/'results'/'distribution_df.csv')
# ax = df.plot(x='current_time', y='feeder_head_voltage', marker='o', linestyle='-', title='Distribution Power Over Time', figsize=(10, 6))
# ax.set_xlabel('Current Time')  # Set the x-axis label
# #ax.set_ylabel('Distribution Power (MW)')  # Set the y-axis label

# plot_path = mydir/'..' / 'results_figures' / 'DistributionSim.png'
# plt.savefig(plot_path)
# plt.close()  # Close the plot frame

# h.helicsFederateFinalize(fed)

# h.helicsFederateFree(fed)
# h.helicsCloseLibrary()
status = h.helicsFederateDisconnect(fed)
h.helicsFederateDestroy(fed)

print("Federate finalized")