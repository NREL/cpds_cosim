import pandas as pd
import numpy as np
import os
import datetime
from pathlib import Path
import matplotlib.pyplot as plt

plt.rcParams['font.size'] = 14


import seaborn as sns
from tqdm import tqdm

mydir = Path(os.path.dirname(__file__))

t_df = pd.read_csv(mydir/'Transmission'/'results'/'transmission_df.csv', index_col=0)
d_df = pd.read_csv(mydir/'Distribution'/'results'/'distribution_df.csv', index_col=0)

t_df = t_df.set_index('current_time')
d_df = d_df.set_index('current_time')

df = pd.concat([t_df,d_df],axis=1)

# Create a figure and a set of subplots
fig, axs = plt.subplots(nrows=2, ncols=1, figsize=(10, 8))  # 2 rows, 1 column

# Plot Temperature
axs[0].plot(df.index, df['distribution_power_mw'], marker='o', color='r')
#axs[0].set_title('Temperature Over Time')
axs[0].set_xlabel('Time (s)')
axs[0].set_ylabel('distribution_power_mw')

# Plot Humidity
axs[1].plot(df.index, df['feeder_head_voltage'], marker='x', color='b')
#axs[1].set_title('Humidity Over Time')
axs[1].set_xlabel('Time (s)')
axs[1].set_ylabel('feeder_head_voltage')

# Add some space between the plots for clarity
plt.tight_layout(pad=3.0)
current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

plt.savefig(mydir/'Results_figures'/f'cosim_plots_{current_time}.png', dpi=300)

print('done')