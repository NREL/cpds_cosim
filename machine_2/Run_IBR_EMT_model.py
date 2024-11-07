# 2024-08-16
# Shuan Dong, Wenbo Wang
# National Renewable Energy Laboratory

import time
import helics as h
from math import pi
import mhi.cosim
import mhi.pscad
import pandas as pd
import numpy as np
import os
import logging
import sys

import opendssdirect as dss

print("Load is okay.")

def config_file(path: str) -> str:
    if os.path.exists(path):
        return path

    raise ValueError("File '" + path + "' does not exist")

def positive_value(value: str) -> float:
    val = float(value)
    if val > 0:
        return val
    raise ValueError("Value must be positive")

cwd = os.getcwd()
cfg_file = os.path.join(cwd, "My_workspace.temp\\cosim_40001.cfg")
run_time = 5.0

fedinitstring = "--federates=1 --broker_address=<IP>:<port number>"
deltat = 0.01

helicsversion = h.helicsGetVersion()

print("PSCAD_DER: Helics version = {}".format(helicsversion))

# Create Federate Info object that describes the federate properties #
fedinfo = h.helicsCreateFederateInfo()

# Set Federate name #
h.helicsFederateInfoSetCoreName(fedinfo, "PSCAD_DER")

# Set core type from string #
h.helicsFederateInfoSetCoreTypeFromString(fedinfo, "tcp_ss")

# Federate init string #
h.helicsFederateInfoSetCoreInitString(fedinfo, fedinitstring)

# Set the message interval (timedelta) for federate. Note th#
# HELICS minimum message time interval is 1 ns and by default
# it uses a time delta of 1 second. What is provided to the
# setTimedelta routine is a multiplier for the default timedelta.

# Set one second message interval #
h.helicsFederateInfoSetTimeProperty(fedinfo, h.helics_property_time_delta, deltat)

# Create value federate #
vfed = h.helicsCreateCombinationFederate("PSCAD_DER", fedinfo)
print("PSCAD_DER: Value federate created")

# Register the publication #
       
PUBLICATIONS = {}
SUBSCRIPTIONS = {}
            
pub = h.helicsFederateRegisterGlobalTypePublication(vfed, "DER/power_p", "double", "")
print("PSCAD_DER: Publication registered")
PUBLICATIONS['DER_p'] = pub


pub = h.helicsFederateRegisterGlobalTypePublication(vfed, "DER/power_q", "double", "")
print("PSCAD_DER: Publication registered")
PUBLICATIONS['DER_q'] = pub

# Register the subscription #
sub = h.helicsFederateRegisterSubscription(vfed, "13Bus/DER_node_voltage", "")
print("PSCAD_DER: Subscription registered")
SUBSCRIPTIONS['13Bus_voltage']=sub

sub = h.helicsFederateRegisterSubscription(vfed, "transmission/bus11/frequency", "")
print("PSCAD_DER: Subscription registered")
SUBSCRIPTIONS['transmission_frequency']=sub

# Enter execution mode #
h.helicsFederateEnterExecutingMode(vfed)
print("PSCAD_DER: Entering execution mode")

# This federate will be publishing deltat*pi for numsteps steps #
this_time = 0.0
value = pi
current_time = -1

total_time = 3
simulation_step_time = 0.02

with mhi.cosim.cosimulation(cfg_file) as cosim:
    channel = cosim.find_channel(1)

    time = 0.0
    time_step = 0.001
    count = 0
        
    Pout_pcc1 = 0
    Qout_pcc1 = 0
    run_time = 5

    for request_time in np.arange(0, total_time, simulation_step_time):
        while current_time < request_time:
            current_time = h.helicsFederateRequestTime(vfed, request_time)
        print(f'=== time step = {current_time} seconds ===')
    
        for key, sub in SUBSCRIPTIONS.items():
            
            if key == '13Bus_voltage':
    
                voltage_opendss = h.helicsInputGetDouble(sub)
                voltage_opendss = float(voltage_opendss)
        
                print(f"Received voltage {voltage_opendss} pu at time {current_time} seconds.")
            if key == 'transmission_frequency':
    
                current_frequency = h.helicsInputGetDouble(sub)
          
                print(f"Received frequency at time {current_time}: {current_frequency} Hz")       
        
        
        # if current_time < 2-simulation_step_time:
        if current_time < simulation_step_time:
            voltage_opendss = 0.96
            current_frequency = 60
            
        while time <= current_time + simulation_step_time:
            
            V_inf_pcc1 = 0.48*voltage_opendss
            Freq_inf_pcc1 = current_frequency
         
            time += time_step
            count += 1
     
            channel.set_value(V_inf_pcc1, 0)
            channel.set_value(Freq_inf_pcc1, 1)
            channel.send(time)
     
            if time <= run_time:
                Pout_pcc1 = channel.get_value(time, 0)
                Qout_pcc1 = channel.get_value(time, 1)
            

            for key, pub in PUBLICATIONS.items():
                if key=='DER_p':
        
                    h.helicsPublicationPublishDouble(pub, Pout_pcc1)
                    print("PSCAD_DER: Sending value power = {} at time {} to OPENDSS_DIS".format(Pout_pcc1, current_time))
                if key=='DER_q':
        
                    h.helicsPublicationPublishDouble(pub, Qout_pcc1)
                    print("PSCAD_DER: Sending value power_q = {} at time {} to OPENDSS_DIS".format(Qout_pcc1, current_time))

h.helicsFederateFinalize(vfed)
print("PSCAD_DER: Federate finalized")

h.helicsFederateFree(vfed)