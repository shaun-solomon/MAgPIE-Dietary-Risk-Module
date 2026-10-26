# import libraries and the dependencies 
from Generate_Exposure_Projections import (
    calculate_proportional_change,
    calculate_exposure_projections,
    add_income_group,
    apply_narrative_adjustments,
    calculate_disease_burden_projections
)
from pathlib import Path
import numpy as np
import pandas as pd

# ------------------------------- FILE PATHS ---------------------------------------------
num_runs = 1
sample_size = 1000

# set unit for marginal
unit_of_marginal = 'DALYs'

# Setup the file paths needed in the final calculation 
rf_morb_mort_path = '../Data/GBD 2017/rf_{}_distributions_without_uncertainty.csv' #risk factors for morbidity and mortality 
TMREL_path = '../Data/GBD 2017/TMREL_distributions_without_uncertainty.csv' 
distribution_weights_path = '../Data/ensemble_distribution_weights.csv'
dietary_risk_factors_path = '../Data/GBD 2017/Dietary_risks_relative_risk_factors_parameters.csv'
min_max_path = '../Data/GBD 2017/relative_exposure_minmax.csv'
dietary_means_path = '../Data/GBD 2017/Exposure Central Values/dietary_means_2017_corrected.csv'
dietary_stds_path = '../Data/GBD 2017/Exposure Central Values/dietary_sd_2017.csv'
M49_path = '../Data/Country_Codes_FAO_GBD_ISO_M49.csv'


# --------------------------------------- GENERATE MEAN EXPOSURE PROJECTIONS -------------------------------------
# Generate projections 
# Ask user for unprocessed MAgPIE output file path 
food_consumption_path = input(
    "Please enter the file path for the unprocessed MAgPIE food consumption projections CSV.\n"
    "Refer to the documentation file for the required data structure and the "
    "recommended location of this CSV file.\n"
    "File path: "
    )

# Use file path provided by user as food-consumption path 
food_consumption_path = Path(food_consumption_path)

# Throw an error if file not found 
if not food_consumption_path.exists():
    raise FileNotFoundError(
        f"Could not find the file: {food_consumption_path}"
    )

# set output file for inspection 
processed_food_consumption_path = (
    Path('../Data/MAgPIE_projections/Processed/')
    / f"{food_consumption_path.stem}_processed{food_consumption_path.suffix}"
    )

processed_food_consumption_path.parent.mkdir(
    parents=True, 
    exist_ok=True
)  # create missing folders and do not error if they already exist

# if the file has already been created continue with calculations 
if processed_food_consumption_path.exists():
    print(f"Using existing proportional-change file: {processed_food_consumption_path}")
    fc_projections_change = pd.read_csv(processed_food_consumption_path)

else: # else generate the proportional-change file
    print("Creating proportional-change file...")

    fc_projections_change = calculate_proportional_change(
        food_consumption_path,
        output_path=processed_food_consumption_path
    )

    # Stop cleanly if proportional change calculation fails 
    if fc_projections_change is None:
        raise ValueError(
            "Proportional-change calculation failed. "
            "Check whether the input MAgPIE file contains baseline year 2020."
        )

dietary_means_projections_path = (
    Path('../Data/Projections/GBD Scaled Exposures/')
    / f"{food_consumption_path.stem}_mean_exposures{food_consumption_path.suffix}"
    )

dietary_means_projections_path.parent.mkdir(parents=True, exist_ok=True) # create any missing folders in the chain and do not throw any error if it exists

# Calculate exposure projections
if dietary_means_projections_path.exists():
    print(f"Using existing exposure projections file: {dietary_means_projections_path}")
    exposure_projections = pd.read_csv(dietary_means_projections_path)
else:
    print("Creating exposure projections file...")

    exposure_projections = calculate_exposure_projections(
        df=fc_projections_change,
        baseline_exposure_path=dietary_means_path,
        country_codes_path=M49_path,
        output_path=dietary_means_projections_path
    )

# --------------------- OPTIONAL NARRATIVE ADJUSTMENTS ---------------------

# Ask user whether narrative adjustments should be applied
use_narrative_adjustments = input(
    "\nWould you like to apply narrative adjustments to the "
    "dietary exposure projections? (y/n): "
).strip().lower()

if use_narrative_adjustments not in ["y", "n"]:
    raise ValueError(
        "Please enter either 'y' or 'n' for narrative adjustments."
    )

use_narrative_adjustments = (
    use_narrative_adjustments == "y"
)

if use_narrative_adjustments:

    # Ask for income-group mapping file
    income_group_path = input(
        "\nPlease enter the file path for the country income-group "
        "classification CSV.\n"
        "The file should contain CountryCode and IncomeGroup columns.\n"
        "File path: "
    )

    income_group_path = Path(income_group_path)

    if not income_group_path.exists():
        raise FileNotFoundError(
            f"Could not find the income-group file: "
            f"{income_group_path}"
        )

    # Ask for narrative-adjustment file
    narrative_adjustment_path = input(
        "\nPlease enter the file path for the narrative-adjustment CSV.\n"
        "The file should contain Risk, SSP, IncomeGroup, "
        "and Adjustment columns.\n"
        "Adjustment values should be percentages "
        "(e.g. 5 = +5%, -5 = -5%).\n"
        "File path: "
    )

    narrative_adjustment_path = Path(
        narrative_adjustment_path
    )

    if not narrative_adjustment_path.exists():
        raise FileNotFoundError(
            f"Could not find the narrative-adjustment file: "
            f"{narrative_adjustment_path}"
        )

    # Add income-group classification
    exposure_projections = add_income_group(
        df=exposure_projections,
        country_codes_path=M49_path,
        income_group_path=income_group_path
    )

    # Set output path for narrative-adjusted exposures
    narrative_exposure_output_path = (
        Path('../Data/Projections/GBD Scaled Exposures/')
        / (
            f"{food_consumption_path.stem}"
            "_mean_exposures_narrative_adjusted"
            f"{food_consumption_path.suffix}"
        )
    )

    # Apply narrative adjustments
    exposure_projections = apply_narrative_adjustments(
        df=exposure_projections,
        narrative_adjustment_path=narrative_adjustment_path,
        apply_adjustments=True,
        output_path=narrative_exposure_output_path
    )

    print(
        "Narrative adjustments successfully applied."
    )

else:
    print(
        "Narrative adjustments will not be applied."
    )

if use_narrative_adjustments:
    dietary_means_model_path = narrative_exposure_output_path
else:
    dietary_means_model_path = dietary_means_projections_path 
    
# --------------------- ANALYSIS TIME POINTS ---------------------
time_points = np.array(
    sorted(
        exposure_projections["Year"]
        .astype(int)
        .unique()
    )
)

print(
    f"\nAnalysis years: {time_points.tolist()}"
)
# --------------------- POPULATION PROJECTIONS ---------------------

population_path = input(
    "\nPlease enter the file path for the population projections CSV.\n"
    "The file should contain country, year, scenario, and value columns.\n"
    "File path: "
)

population_path = Path(population_path)

if not population_path.exists():
    raise FileNotFoundError(
        f"Could not find the population projection file: "
        f"{population_path}"
    )

population_data = pd.read_csv(
    population_path,
    usecols=[
        "country",
        "year",
        "scenario",
        "value"
    ]
)

available_population_scenarios = sorted(
    population_data["scenario"].dropna().unique()
)

print("\nAvailable population scenarios:")

for scenario in available_population_scenarios:
    print(f" - {scenario}")

# --------------------- BAU SCENARIO ---------------------

bau_scenario = input(
    "\nPlease enter the scenario that should be treated as "
    "business-as-usual (BAU): "
).strip()

if bau_scenario not in available_population_scenarios:
    raise ValueError(
        f"'{bau_scenario}' is not a valid BAU scenario. "
        f"Available scenarios are: "
        f"{available_population_scenarios}"
    )

print(
    f"Using {bau_scenario} as the BAU disease-burden scenario."
)

# --------------------- YLL PROJECTIONS ---------------------

YLL_bau_path = input(
    "\nPlease enter the file path for the BAU YLL projections CSV.\n"
    "Expected columns: location, sex, age, cause, year, val.\n"
    "File path: "
)

YLL_bau_path = Path(YLL_bau_path)

if not YLL_bau_path.exists():
    raise FileNotFoundError(
        f"Could not find the YLL projection file: "
        f"{YLL_bau_path}"
    )

YLL_scenario_outputs = calculate_disease_burden_projections(
    disease_burden_path=YLL_bau_path,
    population_path=population_path,
    country_codes_path=M49_path, 
    time_points=time_points,
    bau_scenario=bau_scenario
)

# --------------------- YLD PROJECTIONS ---------------------

YLD_bau_path = input(
    "\nPlease enter the file path for the BAU YLD projections CSV.\n"
    "Expected columns: location, sex, age, cause, year, val.\n"
    "File path: "
)

YLD_bau_path = Path(YLD_bau_path)

if not YLD_bau_path.exists():
    raise FileNotFoundError(
        f"Could not find the YLD projection file: "
        f"{YLD_bau_path}"
    )

YLD_scenario_outputs = calculate_disease_burden_projections(
    disease_burden_path=YLD_bau_path,
    population_path=population_path,
    country_codes_path = M49_path, 
    time_points=time_points,
    bau_scenario=bau_scenario
)



# --------------------- GENERATE INDEX DICTIONARY -----------------------------------------------------
# Generate index dictionary 
yll_causes = set(
    cause
    for df in YLL_scenario_outputs.values()
    for cause in df["cause"].unique()
)

yld_causes = set(
    cause
    for df in YLD_scenario_outputs.values()
    for cause in df["cause"].unique()
)

diseases = np.array(
    sorted(
        yll_causes & yld_causes
    )
)

# --------------------- DEFINE COUNTRIES AVAILABLE IN ALL DATASETS ---------------------

 

exposure_countries = set(
    exposure_projections["Location"]
    .dropna()
    .unique()
)

yll_countries = set(
    country
    for df in YLL_scenario_outputs.values()
    for country in df["location"].dropna().unique()
)

yld_countries = set(
    country
    for df in YLD_scenario_outputs.values()
    for country in df["location"].dropna().unique()
)

# Countries that exist in every required input
valid_countries = (
    exposure_countries
    & yll_countries
    & yld_countries
)

# Countries excluded from the model
dropped_countries = sorted(
    exposure_countries - valid_countries
)

if dropped_countries:

    print(
        "\nWARNING: The following countries will be excluded "
        "from the analysis because complete YLL and/or YLD "
        "information is unavailable:"
    )

    for country in dropped_countries:

        missing_from = []

        if country not in yll_countries:
            missing_from.append("YLL")

        if country not in yld_countries:
            missing_from.append("YLD")

        print(
            f" - {country}: missing "
            f"{' and '.join(missing_from)} data"
        )

    print(
        f"\n{len(dropped_countries)} countries excluded."
    )

countries = np.array(
    sorted(valid_countries)
)

print(
    f"{len(countries)} countries retained for analysis."
)

# ----------------------------GENERATE INDEX DICTIONARY -------------------------

index_dict = {
    "countries": countries,
    "time_points": np.array(sorted(exposure_projections["Year"].unique())),
    "scenario_names": np.array(sorted(exposure_projections["SSP"].unique())),
    "food_scenario": np.array(sorted(exposure_projections["Food_Scenario"].unique())),
    "risks": np.array(sorted(exposure_projections[exposure_projections["Risk"] != "Diet high in saturated fatty acids"]["Risk"].unique())),
    "age_groups": np.array(sorted(exposure_projections["Age Group"].unique())),
    "genders": np.array(sorted(exposure_projections["Sex"].unique())),
    "diseases": diseases
}

# -------------------------------- ADDITIONAL SET-UP ----------------------------------
# setup tuples and lists needed to generate distributions 

dist_parameter_tuples = [('expon', 'scale'), ('gamma', 'scale'), ('gamma', 'a'), ('fisk', 'scale'), ('fisk', 'c'),
                            ('gumbel_r', 'scale'), ('gumbel_r', 'loc'), ('weibull_min', 'scale'),
                            ('weibull_min', 'c'), ('lognorm', 'scale'), ('lognorm', 's'),  ('norm', 'scale'),
                            ('norm', 'loc'), ('beta', 'scale'), ('beta', 'loc'), ('beta', 'a'), ('beta', 'b'),
                            ('mirrored_gamma', 'scale'), ('mirrored_gamma', 'a'), ('mirrored_gumbel_r', 'scale'),
                            ('mirrored_gumbel_r', 'loc'), ('invgamma', 'scale'), ('invgamma', 'a'),
                            ('invweibull', 'scale'), ('invweibull', 'c'), ('limits', 'lower'), ('limits', 'upper')]

distribution_names = ['expon', 'gamma', 'fisk', 'gumbel_r', 'weibull_min', 'lognorm', 'norm', 'beta', 'mirrored_gamma',
                      'mirrored_gumbel_r', 'invgamma', 'invweibull']


