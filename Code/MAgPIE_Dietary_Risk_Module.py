# main file - this is where the main calculations happen. Helper modules and dependencies support calculations in this file 
import numpy as np  
import pandas as pd
from helpers_data_and_setup import calculate_mediation_matrix, calculate_MF_NJ,  calculate_MF_J, load_input_files, \
    load_std, load_means_per_year 
from helpers_PAF_calculation import full_calculation, calculate_PAF_per_disease 
from Distribution_creater_class import DistributionCreator
from Setup_file import num_runs, sample_size, M49_path, index_dict, dietary_stds_path, dietary_means_model_path, \
    dietary_risk_factors_path, rf_morb_mort_path, TMREL_path, food_consumption_path, YLL_scenario_outputs, YLD_scenario_outputs
import time
from pathlib import Path 

'''
################################################
# general setup
################################################
'''

# Import the country M49 codes file
country_codes_df = pd.read_csv(M49_path, index_col=3)
country_codes_df.sort_index(inplace=True)

# Setup all scenarios, time-points, countries, risks, diseases, age groups, genders
scenario_names = index_dict['scenario_names']
num_scenarios = len(scenario_names)
time_points = index_dict['time_points']
num_times = len(time_points)
countries = index_dict['countries']
num_countries = len(countries)
risks = index_dict['risks']
num_risks = len(risks)
diseases = index_dict['diseases']
num_diseases = len(diseases)
age_groups = index_dict['age_groups']
num_ages = len(age_groups)
genders = index_dict['genders']
num_genders = len(genders)

'''
################################################
# output setup
################################################
'''

output_path = (
    Path("../Data/Predictions/")
    / f"{food_consumption_path.stem}_DALYs_per_risk.csv.gz"
)

output_path.parent.mkdir(parents=True, exist_ok=True)

# Start fresh each time
if output_path.exists():
    output_path.unlink()

header_written = False


   
'''
################################################
# loading the data
################################################
'''

# Get the risk factors dataframe from the csv file
risk_factors_df = pd.read_csv(dietary_risk_factors_path, delimiter=';', index_col=[0, 5, 6])
risk_factors_df.sort_index(inplace=True)

# Create risk dictionary, which stores the diseases associated with each risk
risks_dict = {}
for risk in risks:
    risks_dict[risk] = np.unique(risk_factors_df.loc[risk, :].index.get_level_values(0))
    
# Get risk factors dataframes as well as TMREL dataframe
rf_df_morb = pd.read_csv(rf_morb_mort_path.format('morb'), index_col=[0, 1, 2])
rf_df_morb.sort_index(inplace=True)
rf_df_mort = pd.read_csv(rf_morb_mort_path.format('mort'), index_col=[0, 1, 2])
rf_df_mort.sort_index(inplace=True)
TMREL_df = pd.read_csv(TMREL_path, index_col=0)
TMREL_df.sort_index(inplace=True)

# Create the mediation matrix MF
MF = calculate_mediation_matrix()

# get the input files
minmax_bounds_df, distribution_weights_df = load_input_files()

# Setup the DALYs array
M49s = np.zeros(num_countries)

# Introducing a flag to execute non-joint DALY or joint DALY calculation 
calculate_NJ_DALYs = False

overall_begin = time.time()

# Loop over scenarios, time points, and countries
for scenario_idx, scenario_name in enumerate(scenario_names):
    for year_idx, time_point in enumerate(time_points):
        print(f'Calculating for scenario: {scenario_name}, year: {time_point}')
        
        # load the mean values for YLLs and YLDs 
        # Load scenario-specific YLL and YLD projections
        total_YLL_df = (YLL_scenario_outputs[scenario_name].loc[
                lambda df: df["year"] == time_point]
            .set_index(["location", "sex", "age", "cause"]))
        total_YLD_df = (YLD_scenario_outputs[scenario_name].loc[
                lambda df: df["year"] == time_point]
            .set_index([ "location", "sex", "age", "cause" ]))
        

        # Set it up for one country first
        for idx1, country in enumerate(countries):
            print(country)
            
            
            M49s[idx1] = country_codes_df.loc[country, 'UNM49']
            
            # get mean and standard deviation per country
            mean_values_df = load_means_per_year(dietary_means_model_path, scenario_name, time_point, country)
            sd_values_df = load_std(dietary_stds_path, country)
            
            begin = time.time()
            
            # Store aggregated DALYs for this country/scenario/year only
            # Shape: age group × risk
            country_summary = np.zeros((num_ages, num_risks))
            
            # Loop over runs
            for run in np.arange(num_runs):
                print(run)
                attributable_DALYs = np.zeros((num_diseases, num_ages, num_genders, num_risks))
                
                # Load means and standard deviationsnh
                means = mean_values_df["Mean"].to_numpy()
                stds = sd_values_df["Mean_SD"].to_numpy()
                
                # Generate distributions
                distributions_df = \
                    DistributionCreator(
                        country, risks, age_groups, genders, run, sample_size).get_distributions(
                        means, stds, minmax_bounds_df.loc[country, :], distribution_weights_df)
                            
                # Loop over diseases, age groups, and genders
                for idx2, disease in enumerate(diseases):
                    PAF_array = np.zeros((num_ages, 2, len(risks), 2))
                    
                    for idx3, age in enumerate(age_groups):
                        for idx4, gender in enumerate(genders):
    
                            
                            # Loop over risks
                            for idx5, risk in enumerate(risks):
                                risk_diseases = risks_dict[risk]
                                
                                if disease in risk_diseases:
                                    morb_mort = \
                                        np.unique(risk_factors_df.loc[(risk, disease), :].index.get_level_values(0))[0]
                                        
                                    if morb_mort == 'Both':
                                        PAF_value = full_calculation(risk, disease, age, gender, TMREL_df, risk_factors_df,
                                                                     distributions_df, rf_df_morb,
                                                                     rf_df_mort, 'Both', run)
                                        PAF_array[idx3, idx4, idx5, :] = PAF_value
                                        
                                    else: 
                                        PAF_array[idx3, idx4, idx5, 0] = \
                                            full_calculation(risk, disease, age, gender, TMREL_df, risk_factors_df,
                                                             distributions_df, rf_df_morb, rf_df_mort, 'Morbidity', run)
                                        PAF_array[idx3, idx4, idx5, 1] = \
                                            full_calculation(risk, disease, age, gender, TMREL_df, risk_factors_df,
                                                             distributions_df, rf_df_morb, rf_df_mort, 'Mortality', run)
                    for idx3, age in enumerate(age_groups):
                        for idx4, gender in enumerate(genders):
                                    
                            # Calculate total YLDs and YLLs
                            total_YLDs = total_YLD_df.loc[(country, gender, age, disease), 'val']  
                            total_YLLs = total_YLL_df.loc[(country, gender, age, disease), 'val']   
        
                                    
                            # Loop over risks
                            for idx5, risk in enumerate(risks):
                                risk_diseases = risks_dict[risk]
                                
                                if disease in risk_diseases:
                                    morb_mort = \
                                        np.unique(risk_factors_df.loc[(risk, disease), :].index.get_level_values(0))[0]
                                             
                                    # Choose mediation matrix based on the flag
                                    if calculate_NJ_DALYs:
                                        modified_MF = calculate_MF_NJ(risk)
                                        
                                    else: 
                                        modified_MF = calculate_MF_J(MF, risk)
                                    
                                    # Calculate PAF_J for Morbidity and Mortality
                                    PAF_J_Morb = calculate_PAF_per_disease(PAF_array[idx3, idx4, :, 0], modified_MF, idx2)
                                    PAF_J_Mort = calculate_PAF_per_disease(PAF_array[idx3, idx4, :, 1], modified_MF, idx2)
                                    
                                    # Calculate attributable DALYs
                                    attributable_DALY = PAF_J_Morb * total_YLDs + PAF_J_Mort * total_YLLs
                                    
                                    # Store attributable DALYs
                                    attributable_DALYs[idx2, idx3, idx4, idx5] = attributable_DALY
                                    
                # Aggregate over diseases and genders immediately
                # attributable_DALYs shape: disease × age × gender × risk
                country_summary += attributable_DALYs.sum(axis=(0, 2))
                    
                del means
                del stds
              
            # After all runs are complete for this country/scenario/year,
            # write the aggregated result to file
            rows = []

            for age_idx, age in enumerate(age_groups):

                for risk_idx, risk in enumerate(risks):

                    rows.append({
                        "Scenario": scenario_name,
                        "Year": time_point,
                        "Country": country,
                        "Risk": risk,
                        "Age Group": age,
                        "DALY Value": country_summary[age_idx, risk_idx]
                    })

            country_df = pd.DataFrame(rows)

            country_df.to_csv(
                output_path,
                mode='a',
                header=not header_written,
                index=False,
                compression={
                    "method": "gzip",
                    "compresslevel": 5
                }
            )

            header_written = True

            del country_summary
            del country_df
            del rows
            

overall_end = time.time()

print("Total time:", overall_end - overall_begin)
print(f"Saved results to: {output_path}")

                

                           
                                            
                