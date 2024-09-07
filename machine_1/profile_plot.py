import matplotlib.pyplot as plt
import pandas as pd
import os

from pathlib import Path


# Load the data from the file
mydir = Path(os.path.dirname(__file__))
os.chdir(mydir)
file_path = 'profile.txt'
with open(file_path, 'r') as file:
    lines = file.readlines()

# Initialize lists to store parsed data
timestamps = []
components = []
events = []

# Parse each line
for line in lines:
    if "<PROFILING>" in line:
        parts = line.split('>')
        component_raw = parts[1]
        component_name = component_raw.split('[')[0]  # Extracting the component name
        time_part = parts[2].split('[')[-1]
        timestamp = float(time_part.split('=')[1].split(']')[0])
        event = "Start" if "ENTRY" in line else "End"
        components.append(component_name)
        timestamps.append(timestamp)
        events.append(event)

# Create a DataFrame
df = pd.DataFrame({
    'Timestamp': timestamps,
    'Component': components,
    'Event': events
})

# Sort the DataFrame by timestamp to ensure correct order of events
df.sort_values(by=['Component', 'Timestamp'], inplace=True)
df['Timestamp'] = df['Timestamp'].apply(lambda x: 0 if x < 0 else x)
# Plotting
fig, ax = plt.subplots(figsize=(10, 5))
colors = {'Start': 'green', 'End': 'red'}  # Different colors for Start and End events

for component in df['Component'].unique():
    component_df = df[df['Component'] == component]
    for _, row in component_df.iterrows():
        # Plot each event with a different color and marker
        marker = 'o' if row['Event'] == 'Start' else 'x'
        ax.scatter(row['Timestamp'], component, color=colors[row['Event']], marker=marker, label=f"{row['Event']} {component}" if _ == 0 else "")

ax.set_xlabel('Time (seconds)')
ax.set_ylabel('Component')
ax.set_title('Simulation Profiling Timeline')
plt.legend()
plt.grid(True)
plt.show()
