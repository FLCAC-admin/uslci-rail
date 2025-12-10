"""
The purpose of this script is to build olca process objects that will contain
the 2020 NEI derived rail transport data for US class 1 line haul railroads.

TO-DO:
- Finalize process metadata
- Complete dqi in flow meta
"""
#%% SETUP ##

## DEPENDENCIES ##
import pandas as pd
from pathlib import Path
import yaml
from esupy.location import read_iso_3166
from esupy.util import make_uuid
from flcac_utils.util import format_dqi_score

from flcac_utils.util import generate_locations_from_exchange_df
from flcac_utils.generate_processes import build_location_dict
from flcac_utils.util import extract_actors_from_process_meta, \
    extract_sources_from_process_meta, extract_dqsystems
from flcac_utils.generate_processes import build_flow_dict, \
        build_process_dict, write_objects, validate_exchange_data
from flcac_utils.util import assign_year_to_meta

# working directory
working_dir = Path(__file__).parent
data_dir = working_dir / "data"

# Load yaml file for flow meta data
with open(data_dir / 'rail_flow_meta.yaml') as f:
    meta = yaml.safe_load(f)

# Load yaml file for process meta data
with open(data_dir / 'rail_process_meta.yaml') as f:
    process_meta = yaml.safe_load(f)

# Read in CSV file created by 'commodity transport distances.py'
csv_path = data_dir / 'RAIL_LCI_INVENTORY.csv'
df_olca = pd.read_csv(csv_path)

#df_olca = df_olca.drop(columns=['Mass Shipped (kg)', 'Avg. Dist. Shipped (km)', 'Mass Frac. by Mode'])

# Create empty df_olca that includes all schema requirements
schema = ['ProcessID',
          'ProcessCategory',
          'ProcessName',
          'FlowUUID', 
          'FlowName',
          'Context',
          'IsInput', 
          'FlowType', 
          'reference', 
          'default_provider',
          'default_provider_name',
          #'amount',
          #'unit',
          'avoided_product',
          'exchange_dqi',
          'location']

# Add schema columns to df_olca
for column in schema:
    df_olca[column] = ''
    
# Move values from 'Weighted Dist. Shipped (km)' to 'amount'
# Remove 'Weighted Dist. Shipped (km)' column
#df_olca['amount'] = df_olca['Weighted Dist. Shipped (km)']
#df_olca.drop('Weighted Dist. Shipped (km)', axis=1, inplace=True)


#%% Add values for inputs ###
df_olca['IsInput'] = df_olca['data name'].apply(lambda x: True if x == 'diesel' else False)
df_olca['reference'] = False
df_olca['ProcessName'] = 'Transport, rail, freight; diesel powered; tier ' + df_olca['tier']
df_olca['ProcessID'] = df_olca['ProcessName'].apply(make_uuid)


#%% 
# Map flow name based on flow name mapping to fedefl in rail_flow_meta.yaml
df_olca['FlowName'] = df_olca['data name'].map(
    {k: v['FlowName'] for k, v in meta['Flows'].items()})

# Map flow uuid based on flow name mapping to fedefl in rail_flow_meta.yaml
df_olca['FlowUUID'] = df_olca['data name'].map(
    {k: v['FlowUUID'] for k, v in meta['Flows'].items()})

# Map default provider name based on flow name mapping to fedefl in rail_flow_meta.yaml
df_olca['default_provider_name'] = df_olca['data name'].map(
    {k: v['ProcessName'] for k, v in meta['Flows'].items()})

# Map default provider uuid based on flow name mapping to fedefl in rail_flow_meta.yaml
df_olca['default_provider'] = df_olca['data name'].map(
    {k: v['DefaultProviderUUID'] for k, v in meta['Flows'].items()})

# %% overwrite UUIDs for average unit process based on what previously existed in USLCI

target = 'Transport, rail, freight; diesel powered; tier weighted average'
uuid = '7de9c230-fd0f-3478-be87-f80181132faa'

mask = df_olca['ProcessName'].str.contains(target, regex=False, na=False)
df_olca.loc[mask, 'ProcessID'] = uuid


#%% Create new flows for the reference flow of each process ###

# Get unique tiers
unique_tier = df_olca['tier'].unique()

# Creat list for dictionaries of ref flow values
new_rows = []
for tier in unique_tier:
    
    # Get process uuid and name for each new ref flow
    processID = df_olca[df_olca['tier'] == tier]['ProcessID'].iloc[0]
    processName = df_olca[df_olca['tier'] == tier]['ProcessName'].iloc[0]
    
    # Create FlowName by modifying the commodity string
    flowName = f"Transport, rail, freight; diesel powered; emissions tier {tier}"
    if tier == 'weighted average':
        flowUUID = '73c7494d-4e93-3769-896b-8bb82f0dfccc'
    # generate reference flow uuid
    else:
        flowUUID = make_uuid([flowName, processName, processID])

    # Create the new row as a dictionary
    new_row = {
        'tier': tier,
        'ProcessID': processID,
        'ProcessName': processName,
        'FlowName': flowName,
        'FlowUUID': flowUUID,
        'IsInput': False,
        'reference': True,
        'amount': 1.0,
        'unit': 't*km',
        'default_provider': 'nan',
        'default_provider_name': 'nan'
    }
    new_rows.append(new_row)

# Convert new rows to DataFrame
new_df = pd.DataFrame(new_rows)

# Append to original DataFrame
df_olca = pd.concat([df_olca, new_df], ignore_index=True)


#%% Add values shared by both inputs and ref flow

df_olca['ProcessCategory'] = '48-49: Transportation and Warehousing/ 4821: Rail Transportation'

df_olca['Context'] = 'Technosphere flows / 48-49: Transportation and Warehousing / 4821: Rail Transportation'
df_olca['FlowType'] = 'PRODUCT_FLOW'
df_olca['avoided_product'] = False
df_olca['location'] = 'US'
df_olca['Year'] = 2020

# %% re-locate the fuel


target2 = 'Diesel, at refinery'
diesel_location = 'Technosphere flows / 31-33: Manufacturing / 3241: Petroleum and Coal Products Manufacturing'

mask = df_olca['FlowName'].str.contains(target2, regex=False, na=False)
df_olca.loc[mask, 'Context'] = diesel_location


#%% Assign exchange dqi
df_olca['exchange_dqi'] = format_dqi_score(meta['DQI']['Flow'])


#%% Assign locations to processes
df_olca = df_olca.merge(read_iso_3166().
                            filter(['ISO-2d', 'ISO-3d'])
                            .rename(columns={'ISO-3d': 'CountryCode',
                                             'ISO-2d': 'location'}),
                        how='left')
locations = generate_locations_from_exchange_df(df_olca)


#%% Build supporting objects


(process_meta, source_objs) = extract_sources_from_process_meta(
   process_meta, bib_path = data_dir / 'rail_sources.bib')

(process_meta, actor_objs) = extract_actors_from_process_meta(process_meta)

dq_objs = extract_dqsystems(meta['DQI']['dqSystem'])

process_meta['dq_entry'] = format_dqi_score(meta['DQI']['Process'])

# generate dictionary of location objects
location_objs = build_location_dict(df_olca, locations)


#%% Create json file


validate_exchange_data(df_olca)
flows, new_flows = build_flow_dict(df_olca)
processes = {}
for year in df_olca.Year.unique():
    ### *** I dont think this is relevant since we have 1 year of data
    #process_meta = assign_year_to_meta(process_meta, year)
    # Update time period to match year for each region

    p_dict = build_process_dict(df_olca.query('Year == @year'),
                                flows,
                                meta=process_meta,
                                loc_objs=location_objs,
                                source_objs=source_objs,
                                actor_objs=actor_objs,
                                dq_objs=dq_objs,
                                )
    processes.update(p_dict)
    
out_path = working_dir / 'output'
out_path.mkdir(exist_ok=True)
write_objects('rail-transport', flows, new_flows, processes,
              location_objs, dq_objs, source_objs,
              out_path = out_path
              )

#%% Unzip files to repo
from flcac_utils.util import extract_latest_zip

extract_latest_zip(out_path,
                   working_dir,
                   output_folder_name = out_path / 'uslci-rail_v1.0')
