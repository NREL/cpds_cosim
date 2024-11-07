"""
Code for transmission model
by NREL wenbo wang
4/11/2024

"""


import time
from datetime import datetime

import os
import sys
from pathlib import Path
import json
import helics as h
import numpy as np
import pandas as pd
# import pssepath
# pssepath.add_pssepath()

sys_path_PSSE=r'C:\\Program Files\\PTI\\PSSE35\\35.6\\PSSPY38'
sys.path.append(sys_path_PSSE)
os.environ['PATH'] += ';' + sys_path_PSSE


import psse35
import dyntools

import redirect
redirect.psse2py()
import psspy

import re
import pssplot

mydir = Path(os.path.dirname(__file__))
psse_file_dir = mydir/'ieee_14'
os.chdir(mydir)

raw_file = str(psse_file_dir/'ieee14.raw')
# sav_file = str(psse_file_dir/'ieee14.cnv')
#dyr_file = str(psse_file_dir/'ieee14.dyr')
sav_file = str(psse_file_dir/'ieee14_reduced_inertia.cnv')



out_file = str(psse_file_dir/'ieee14_run_trip_reduced_inertia.outx')
snp_file = str(psse_file_dir/'ieee14_reduced_inertia.snp')

filename = "TransmissionSim.json"
with open(filename) as f:
    data = json.loads(f.read())
    federate_name = data["name"]
    total_time = data["total_time"]
    #step_time = data["step_time"]
    subscriptions = data["subscriptions"]
    publications = data["publications"]
    simulation_step_time = data["simulation_step_time"]
print("reading json okay!")
PUBLICATIONS = {}
SUBSCRIPTIONS = {}
# start a broker inside the file
# brokerinitstring = "-f 2 --name=mainbroker" # 3 is the number of federates connecting

# Create broker #
# broker = h.helicsCreateBroker("zmq", "", brokerinitstring)
# isconnected = h.helicsBrokerIsConnected(broker)
# if isconnected == 1:
#     print("Broker created and connected")


fedinfo = h.helicsCreateFederateInfo()
#fedinitstring = "--broker=mainbroker --federates=1" # this string is for defining the core
#fedinitstring = "--federates=1" # this string is for defining the core
fedinitstring = '--federates=1 --broker_address=<IP>:<port number>'
h.helicsFederateInfoSetCoreName(fedinfo, f"{federate_name}") # define name
h.helicsFederateInfoSetCoreTypeFromString(fedinfo, "tcp_ss") # core type
h.helicsFederateInfoSetCoreInitString(fedinfo, fedinitstring) # define number fo federate and tell the federate it is the main broker
h.helicsFederateInfoSetTimeProperty(fedinfo, h.helics_property_time_delta, 0.01)
#h.helicsFederateInfoSetLoggingLevel(fedinfo, 5)  # from loglevel in json

# create value federate based on federate info: this type of federate is used for exchange electrical information
fed = h.helicsCreateCombinationFederate(f"{federate_name}", fedinfo)
print(f"{federate_name}: Combination federate created", flush=True)

# register the publication
for k, v in publications.items():
    pub = h.helicsFederateRegisterGlobalTypePublication(fed, v['topic'], v['type'], "") # register to helics
    PUBLICATIONS[k] = pub # store the HELICS object

for k, v in subscriptions.items():
    sub = h.helicsFederateRegisterSubscription(fed, v['topic'], "")
    SUBSCRIPTIONS[k] = sub  # store the HELICS object


############### Entering Execution Mode ########################
h.helicsFederateEnterExecutingMode(fed)
print(f"{federate_name}: Entering execution mode", flush=True)

start_time = time.time()

# psse input snp and save file

psspy.psseinit(1000000)
psspy.case(sav_file)
psspy.rstr(snp_file)

print('->> Loading psse OK ...')

psspy.progress_output(islct=2, filarg="./psse_run_progress_output.txt",options=[0,0]) # 1 is to display
# psspy.prompt_output(islct=2, filarg="./psse_run_prompt_output.txt",options=[0,0])
# psspy.report_output(6,"",[0,0])
# psspy.alert_output
# Redirect generated reports to a file
psspy.report_output(islct=1, filarg="./psse_run_report_output.txt", options=[0,0])

# psspy.voltage_channel([-1,-1,-1,2],r"""VOLT-COSTA SUR115 115 kV""")

# psspy.voltage_channel([-1,-1,-1,98],r"""VOLT-HUMACAO TC""")

psspy.chsb(0,1,[-1,-1,-1,1,13,0]) # this is to add all voltage channel

psspy.chsb(0,1,[-1,-1,-1,1,12,0]) # this is to add all freq channel


#psspy.bus_frequency_channel([-1,98],r"""FREQ-HUMACAO TC""")


#psspy.bus_frequency_channel([-1,2],r"""FREQ-COSTA SUR115 115 kV""")

psspy.set_osscan(1,0) # a simulation setting scan for out of step conditions
psspy.set_genang_2(1, 200.0,0.0) # the simulation option setting that scans for generators for which the angle
#differs from the angular average by more than a specified threshold
psspy.set_vltscn(1, 1.2, 0.5)
psspy.set_volt_viol_subsys_flag(0)
psspy.set_voltage_dip_check(1, 0.8, 0.2)
psspy.set_voltage_rec_check(1,0, 0.8, 0.4, 0.9, 1.0)


psspy.text("")
psspy.text(r""" ****** SYSTEM TOTALS ******""")
psspy.text("")
psspy.area_2(0,1,1)
psspy.text("")
psspy.text("")
psspy.text(r""" ****** VCHECK ******""")
psspy.text("")
psspy.vchk(0,1, 0.95, 1.05)
psspy.text("")


run_to = total_time

now = datetime.now() # record the time
append_time = now.strftime("%m_%d_%Y_%H_%M_%S")
#file_str = der_case + '_flat_fault_'+ append_time + '.outx'
#output_str = str(mydir/'psse_outx'/file_str)

#psspy.strt_2([0,1],r"""flatstart_fault_1.outx""") # initialize a PSSE dynamic simulation for state-space simulations
psspy.strt_2([0,1], out_file)

print("=========================")
print("->> Simulation start ...")

flat_start_time = simulation_step_time
psspy.run(0, flat_start_time,1,1,0)


ierr, buses_data = psspy.abusint(sid=-1, string="NUMBER")  # Get bus voltages and angles
if ierr != 0:
    print("Error retrieving bus data")
else:
    bus_numbers = buses_data[0]


ierr, buses_data = psspy.abusreal(sid=-1, string=["PU", "ANGLED"])  # Get bus voltages and angles
if ierr != 0:
    print("Error retrieving bus data")
else:
    voltages_pu = buses_data[0]
    angles_deg = buses_data[1]

end_time1 = time.time()
elapsed_time1 = round(end_time1 - start_time)
elapsed_time_min1 = round(elapsed_time1/60)
# Print the elapsed time
print("Flat start 1 sec Dynamic run uses time:", elapsed_time1, "seconds (=", elapsed_time_min1, "minutes).")

Trip_scenario = True
Fault_scenario = False
Normal_scenario = False
############################


current_time = 0

#scale_p = 0.09/0.03569
p_list = []
current_time_list = []
trip_time = 0.5
fault_time = 2
trip_already = False

for request_time in np.arange(0, total_time, simulation_step_time):
    while current_time < request_time:
        current_time = h.helicsFederateRequestTime(fed, request_time)

    current_time_list.append(current_time)
    print(f'=== time step = {current_time} seconds ===')

    if Trip_scenario and not trip_already:
        if current_time > trip_time:
            psspy.dist_machine_trip(8,'1')
            trip_already = True
            print('This trip should be once!')

        # if (current_time > trip_time - simulation_step_time) and (current_time < trip_time + simulation_step_time):
        #     psspy.dist_machine_trip(8,'1')
        #     print("Trip machine applied") 

    if Fault_scenario:
        if (current_time > fault_time-0.1) and (current_time < fault_time + 0.1):
            
            psse_time = current_time - simulation_step_time
            print(f"Fault scenario applied at time {psse_time} seconds")
            psspy.dist_bus_fault(5, 1, 230, (0,-2.0E11)) # 0.001, 0.001
            clearing_time = current_time - simulation_step_time + 0.05
            print(f"clearing_time = {clearing_time} seconds")
            psspy.run(0, clearing_time,1,1,0)    
            print(f'clearing fault!')
            psspy.dist_clear_fault()
    
    print(f'current_time = {current_time}')
    psspy.run(0, current_time, 1, 1, 0)
    
    ierr, psse_current_time = psspy.dsrval('TIME', 0)
    print(f'psse_current_time = {psse_current_time}')

    ierr, buses_data = psspy.abusint(sid=-1, string="NUMBER")  # Get bus voltages and angles
    if ierr != 0:
        print("Error retrieving bus data")
    else:
        bus_numbers = buses_data[0]
    
    # retrieve frequency
    chnfobj = dyntools.CHNF(out_file)

    short_title, chanid, chandata = chnfobj.get_data()
    chanid[51] # this is bus 11 frequnecy
    current_frequency_delta = chandata[51][-1]

    current_frequency = (1+current_frequency_delta)*60

    assert current_frequency_delta is not None, "Frequency delta is None"
    assert isinstance(current_frequency_delta, (int, float)), "Frequency delta is not a number"

    # retrieve voltage

    ierr, buses_data = psspy.abusreal(sid=-1, string=["PU", "ANGLED"])  # Get bus voltages and angles
    if ierr != 0:
        print("Error retrieving bus data")
    else:
        voltages_pu = buses_data[0]
        angles_deg = buses_data[1]
    
    for key, sub in SUBSCRIPTIONS.items():
        if subscriptions[key]['value']=='Powers': # power meaning it is for distribution systems
            #if current_time % subscriptions[key]['sub_interval']<=1e-6:
            val = h.helicsInputGetDouble(sub) # val is P, Q
            #h.helicsInputGetComplex(sub)
            bus_name = subscriptions[key]['element_name']
            bus_PQ_index = int(subscriptions[key]['bus_PQ_index'])
            
            P = val
            print(f"Received active power from {key} at time {current_time}: {P} kw")
            print(f"for bus_name={bus_name}, bus_PQ_index={bus_PQ_index} ")
            #print("Received reactive power (not use) from {} at time {}: {} kvar".format(key, current_time, Q))
            # convert to pu
            #P = P/1e3*scale_p
            P = P/1e3 # MW
            #Q = Q/1e5

            if current_time < simulation_step_time:

                print("manually set up first step load bus P and Q")
                P = 0
                Q = 0

            else:

                bus_number = int(bus_name)
                load_id = '1'
                new_active_power = P
                ierr = psspy.load_chng_5(bus_number, load_id, [], [new_active_power])
                if ierr != 0:
                    print(f"Error updating load: {ierr}")
                else:
                    print(f"updating load fine")
            p_list.append(P)

        ## get the PUBLICATION OUT
    for key, pub in PUBLICATIONS.items():
        # get voltage and angle and publish
        if publications[key]['value']=='Voltage':
            bus_name = publications[key]['element_name']
            element_type = publications[key]['element_type']

            val1 = voltages_pu[int(bus_name)-1]
             
            val2 = angles_deg[int(bus_name)-1]

            # decide when to publish based on pub_interval
            #if current_time % publications[key]['pub_interval']<=1e-6:
            print("Sent voltage mag at time {}: {} pu from {} {}".format(current_time, val1, element_type, bus_name))
            print("Sent voltage ang at time {}: {} deg from {} {}".format(current_time, val2, element_type, bus_name))
            h.helicsPublicationPublishVector(pub, [val1, val2])

        if publications[key]['value']=='Frequency':
            bus_name = publications[key]['element_name']
            element_type = publications[key]['element_type']

            #current_frequency
            print(f"Sent Frequency at time {current_time}: {current_frequency} Hz")
            h.helicsPublicationPublishDouble(pub, current_frequency)

# list all output channel
#ierr = psspy.list_channel_models(0)

status = h.helicsFederateDisconnect(fed)
h.helicsFederateDestroy(fed)
print('Federate finalized')

df = pd.DataFrame()
df['current_time'] = current_time_list
df['distribution_power_mw'] = p_list
df.to_csv(mydir/'results'/'transmission_df.csv')
# ax = df.plot(x='current_time', y='distribution_power_mw', marker='o', linestyle='-', title='Distribution Power Over Time', figsize=(10, 6))
# ax.set_xlabel('Current Time')  # Set the x-axis label
# ax.set_ylabel('Distribution Power (MW)')  # Set the y-axis label

# plot_path = mydir/'..' / 'results_figures' / 'TransmissionSim.png'
# plt.savefig(plot_path)
# plt.close()  # Close the plot frame


end_time2 = time.time()
elapsed_time2 = round(end_time2 - end_time1)
elapsed_time_min2 = round(elapsed_time2/60)


# Print the elapsed time
print("Run to 10 sec Dynamic run uses time:", elapsed_time2, "seconds (=", elapsed_time_min1, "minutes).")


print(f'Saved output to {out_file}')
# psspy.text("")
# psspy.text(r""" ****** SYSTEM TOTALS ******""")
# psspy.text("")
# psspy.area_2(0,1,1)
# psspy.text("")
# psspy.text("")
# psspy.text(r""" ****** VCHECK ******""")
# psspy.text("")
# psspy.vchk(0,1, 0.95, 1.05)
# psspy.text("")
