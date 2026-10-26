# pre-processing script containing functions used to convert MAgPIE food intake projections to dietary risk exposure projections needed by the GBD emulator 

# load libraries/dependencies 
import pandas as pd 
import numpy as np 
from pathlib import Path

'''
#################################################
# Calculate Proportional Change 
#################################################
'''
def calculate_proportional_change (food_consumption_path, output_path):
    """
    Parameters
    ----------
    food_consumption_path (str): relative file path where the MAgPIE food consumption projection files are stored.
    output_path (str): Path where the processed CSV should be saved.
    Returns
    -------
    Neatened df with proportional changes from baseline year (2020) for each food group, country, and time-point comb.

    """
    # Load projections
    fc_projections = pd.read_csv(food_consumption_path, index_col=[0, 1, 2, 3], header=0)
    fc_projections.sort_index(inplace=True)

    # Check whether 2020 exists in the Year index level
    if 2020 not in fc_projections.index.get_level_values("Year"):
        print("Baseline year is missing")
        return None
    
    # Make Country, Year, Scenario and Product normal columns again
    fc_projections = fc_projections.reset_index()

    # Pivot so every product becomes a column
    fc_projections_pivot = fc_projections.pivot(
        index=["Country", "Year", "Scenario"],
        columns="Product",
        values="Value"
    )

    # Define composite food groups
    composite_groups = {
        "red_meat": [
            "livst_rum",
            "livst_pig"
        ],
        "fiber": [
            "puls_pro",
            "brans",
            "tece",
            "trce",
            "others"
        ],
        "proc_meat": [
            "livst_rum",
            "livst_pig",
            "livst_chick"
        ],
        "whole_grains": [
            "maiz",
            "brans",
            "tece",
            "trce",
            "rice_pro"
        ],
        "legumes": [
            "puls_pro",
            "soybean"
        ]
    }

    # Create the composite food-group columns
    for group_name, products in composite_groups.items():
        fc_projections_pivot[group_name] = (
            fc_projections_pivot[products].sum(axis=1)
        )

    # Turn index levels back into ordinary columns
    fc_projections_pivot = fc_projections_pivot.reset_index()
    
    # Keep only the food groups and proxies needed for later 
    food_groups = [
        "red_meat",
        "fiber",
        "proc_meat",
        "whole_grains",
        "legumes",
        "others",
        "fish",
        "livst_chick",
        "livst_milk",
        "oils",
        "sugar",
        "puls_pro"
    ]

    fc_projections_pivot = fc_projections_pivot[
        ["Country", "Year", "Scenario"] + food_groups
    ]
    
    # Generate proportional change 
    baseline_2020 = fc_projections_pivot[
        fc_projections_pivot['Year'] == 2020].copy() #create a copy for 2020 values 
    
    baseline_2020 = baseline_2020.drop(columns = ['Year'])
    
    # rename columns so that they are clear after merging 
    baseline_2020 = baseline_2020.rename(
        columns =
        {food_group: f"{food_group}_2020"
         for food_group in food_groups
         }
        )
    
    fc_projections_change = fc_projections_pivot.merge(baseline_2020, on = 
                                                      ['Country', 'Scenario'], how = 'left') # merge
    # proportional change calculation 
    for food_group in food_groups: 
        fc_projections_change[f"{food_group}_change"] = (
            fc_projections_change[food_group]/fc_projections_change[f"{food_group}_2020"] - 1)
    
        # replace missing values and infinity with 0
        fc_projections_change[f"{food_group}_change"] = (
        fc_projections_change[f"{food_group}_change"]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0))
    
    # Save output file for inspection 
    fc_projections_change.to_csv(output_path, index=False)

    print(f"Saved proportional-change file to: {output_path}")
    
    return fc_projections_change

'''
############################################################
# Calculate Exposure Projections
############################################################
'''
def calculate_exposure_projections (df, baseline_exposure_path, country_codes_path, output_path): 
    """
    Parameters
    ----------
    food_consumption_change_path (str): file path containing proportional change values relative to 2020
    baseline_exposure_path (str): file path containing baseline mean exposure values 
    country_codes (str): ISO3 country codes 
    output_path (str): 
    Returns
    -------
    mean exposure value projections
    """
    
    # load country codes
    country_codes = pd.read_csv(country_codes_path, 
                                usecols = ["GBD_2017_name", "ISO3"], 
                                header = 0)
    
    # Use the input dataframe
    fc_projections_change = df.copy()       
    
    fc_projections_change.rename(columns = 
                                 {"Country" : "ISO3"}, inplace = True)
    
    # merge 
    fc_projections_change = fc_projections_change.merge(country_codes, on = "ISO3", how = "inner")
    
    # rename columns to merge with mean dietary exposure values 
    fc_projections_change.rename(columns =
                                    {"GBD_2017_name" : "Location"}, inplace = True)
    
    # load mean dietary exposure values 
    mean_exposures = pd.read_csv(baseline_exposure_path, header = 0)
    
    # create a mapping matrix linking GBD dietary risk categories with MAgPIE food product categories 
    risk_to_food_change = {
        "Diet high in red meat": "red_meat_change",
        "Diet high in processed meat": "proc_meat_change",
        "Diet low in fiber": "fiber_change",
        "Diet low in whole grains": "whole_grains_change",
        "Diet low in legumes": "legumes_change",
        "Diet low in fruits": "others_change",
        "Diet low in vegetables": "others_change",
        "Diet low in nuts and seeds": "others_change",
        "Diet low in seafood omega-3 fatty acids": "fish_change",
        "Diet low in milk": "livst_milk_change",
        "Diet low in calcium" : "livst_milk_change",
        "Diet low in polyunsaturated fatty acids": "oils_change",
        "Diet high in sugar-sweetened beverages": "sugar_change"
    }
    
    # Add a column to mean exposure values to indicate associated mapping 
    mean_exposures["food_change_col"] = mean_exposures["Risk"].map(
        risk_to_food_change
        )
    
    #Rename projection year to avoid conflict with baseline exposure year 
    fc_projections_change = fc_projections_change.rename(
        columns = {"Year" : "Projection_Year",
                   "Scenario" : "Food_Scenario"})
    fc_projections_change["SSP"] = (
        fc_projections_change["Food_Scenario"].str.extract(r"(SSP[1-5])"))

    # Keep only columns needed from food projections
    change_cols = list(risk_to_food_change.values())
    change_cols = list(set(change_cols))

    fc_projections_change = fc_projections_change[
        ["Location", "Projection_Year", "Food_Scenario", "SSP"] + change_cols
    ]

    # Merge food changes onto baseline exposures by country/location
    exposure_projections = mean_exposures.merge(
        fc_projections_change,
        on="Location",
        how="inner"
    )

    # For each row, get the correct proportional-change value
    def get_proportional_change(row):
        food_change_col = row["food_change_col"]
    
        if pd.isna(food_change_col):
            return 0
    
        return row[food_change_col]

    exposure_projections["proportional_change"] = exposure_projections.apply(
        get_proportional_change,
        axis=1
    )
    
    exposure_projections["proportional_change"] = (
    exposure_projections["proportional_change"]
    .replace([np.inf, -np.inf], np.nan)
    .fillna(0)
    )

    # Allow very large reductions, but prevent exact zero exposure means
    exposure_projections["proportional_change"] = (
        exposure_projections["proportional_change"]
        .clip(lower=-0.999999)
    )

    # Calculate projected exposure values
    exposure_projections["Mean"] = (
        exposure_projections["Mean"]
        * (1 + exposure_projections["proportional_change"])
    )

    # Keep final columns similar to original exposure file
    exposure_projections = exposure_projections[
        [
            "Risk",
            "Location",
            "Projection_Year",
            "Food_Scenario",
            "SSP",
            "Age Group",
            "Sex",
            "Unit",
            "Mean",
        ]
    ]

    exposure_projections = exposure_projections.rename(
        columns = {'Projection_Year' : 'Year'})
    # Save output
    exposure_projections.to_csv(output_path, index=False)

    print(f"Saved exposure projections to: {output_path}")

    return exposure_projections


#-------------------- ADD INCOME GROUP ---------------------
def add_income_group(df, country_codes_path, income_group_path):
    """
    Add ISO3 country codes and income-group classifications to the exposure-projection dataframe.

    Parameters
    ----------
    df (pandas.DataFrame): Exposure projections containing a 'Location' column with GBD 2017 country names.
    country_codes_path : str
    income_group_path : str
    Returns
    -------
    Exposure projections with ISO3 and IncomeGroup columns added.
    """
    exposure_projections = df.copy()
    
    # Load GBD country-name to ISO3 mapping
    country_codes = pd.read_csv(
        country_codes_path,
        usecols=["GBD_2017_name", "ISO3"],
        header=0
    )

    # Rename so that it matches exposure projections
    country_codes = country_codes.rename(
        columns={"GBD_2017_name": "Location"}
    )

    # Add ISO3 codes
    exposure_projections = exposure_projections.merge(
        country_codes,
        on="Location",
        how="left"
    )

    # Load ISO3 to income-group mapping
    income_groups = pd.read_csv(
        income_group_path,
        usecols=["CountryCode", "IncomeGroup"],
        header=0
    )

    # Rename country-code column to match ISO3
    income_groups = income_groups.rename(
        columns={"CountryCode": "ISO3"}
    )

    # Add income-group classification
    exposure_projections = exposure_projections.merge(
        income_groups,
        on="ISO3",
        how="left"
    )

    # Check whether any countries failed to map
    missing_income_groups = exposure_projections.loc[
        exposure_projections["IncomeGroup"].isna(),
        ["Location", "ISO3"]
    ].drop_duplicates()

    if not missing_income_groups.empty:
        print(
            "Warning: income group could not be assigned to "
            "the following countries:"
        )
        print(missing_income_groups)

    return exposure_projections

#-------------------- APPLY NARRATIVE ADJUSTMENTS ---------------------
def apply_narrative_adjustments(df, narrative_adjustment_path, apply_adjustments=True, output_path=None):
    """
    Apply optional narrative adjustments to projected dietary-risk
    mean exposures.

    Parameters
    ----------
    df : Exposure projections containing:
    narrative_adjustment_path (str)
    apply_adjustments : bool, default=True - If False, narrative adjustments are not applied.
    output_path : Optional path where the adjusted exposure projections
        should be saved.
        
    Returns
    -------
    Exposure projections with narrative adjustments applied.
    """

    exposure_projections = df.copy()

    # Allow narrative adjustments to be switched off
    if not apply_adjustments:
        print("Narrative adjustments are turned off.")

        if output_path is not None:
            exposure_projections.to_csv(
                output_path,
                index=False
            )

            print(
                f"Saved exposure projections to: {output_path}"
            )

        return exposure_projections

    # Load narrative-adjustment file
    narrative_adjustments = pd.read_csv(
        narrative_adjustment_path,
        header=0
    )

    # Check required columns
    required_columns = [
        "Risk",
        "SSP",
        "IncomeGroup",
        "Adjustment"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in narrative_adjustments.columns
    ]

    if missing_columns:
        raise ValueError(
            "Narrative-adjustment file is missing columns: "
            f"{missing_columns}"
        )

    # Check for duplicate adjustment definitions
    duplicate_rows = narrative_adjustments.duplicated(
        subset=["Risk", "SSP", "IncomeGroup"],
        keep=False
    )

    if duplicate_rows.any():
        duplicates = narrative_adjustments.loc[
            duplicate_rows,
            ["Risk", "SSP", "IncomeGroup"]
        ]

        raise ValueError(
            "Duplicate narrative adjustments found for:\n"
            f"{duplicates}"
        )

    # Merge narrative assumptions onto projected exposures
    exposure_projections = exposure_projections.merge(
        narrative_adjustments,
        on=["Risk", "SSP", "IncomeGroup"],
        how="left"
    )

    # If no narrative adjustment exists, use 0%
    exposure_projections["Adjustment"] = (
        exposure_projections["Adjustment"]
        .fillna(0)
    )

    # Keep exposure before narrative adjustment for validation
    exposure_projections["Mean_before_narrative"] = (
        exposure_projections["Mean"]
    )

    # Apply narrative adjustment
    #
    #  5  -> multiply by 1.05
    # -5  -> multiply by 0.95
    exposure_projections["Mean"] = (
        exposure_projections["Mean"]
        * (
            1
            + exposure_projections["Adjustment"] / 100
        )
    )

    # Prevent impossible negative exposure values
    exposure_projections["Mean"] = (
        exposure_projections["Mean"]
        .clip(lower=0)
    )

    # Save output if requested
    if output_path is not None:
        exposure_projections.to_csv(
            output_path,
            index=False
        )

        print(
            "Saved narrative-adjusted exposure projections to: "
            f"{output_path}"
        )

    return exposure_projections

# -------------------- CALCULATE DISEASE BURDEN PROJECTIONS ---------------------
def calculate_disease_burden_projections(disease_burden_path, population_path, country_codes_path, time_points, bau_scenario):
    """
    Generate scenario-specific YLL or YLD projections by scaling BAU disease-burden values according to scenario-specific population projections.

    Parameters
    ----------
    disease_burden_path (str): Path to the BAU YLL or YLD projection CSV.
    population_path (str): Path to population projections in long format.
    time_points : list or array-like
    bau_scenario (str): Scenario to use as the business-as-usual reference.

    Returns
    -------
    dict
        Dictionary containing one projected disease-burden dataframe
        for each scenario.
    """
    # Convert paths to Path objects
    disease_burden_path = Path(disease_burden_path)
    population_path = Path(population_path)

    # Check if files exist

    if not disease_burden_path.exists():
        raise FileNotFoundError(
            f"Could not find disease-burden file: "
            f"{disease_burden_path}"
        )

    if not population_path.exists():
        raise FileNotFoundError(
            f"Could not find population file: "
            f"{population_path}"
        )

    # Load files

    disease_burden = pd.read_csv(
        disease_burden_path,
        usecols=[
            "location",
            "sex",
            "age",
            "cause",
            "year",
            "val"
        ]
    )

    population = pd.read_csv(
        population_path,
        usecols=[
            "country",
            "year",
            "scenario",
            "value"
        ]
    )
    
    # Map GBD country names to ISO3

    country_codes = pd.read_csv(
        country_codes_path,
        usecols=[
            "GBD_2017_name",
            "ISO3"
        ]
    )
    
    disease_burden = disease_burden.merge(
        country_codes,
        left_on="location",
        right_on="GBD_2017_name",
        how="left",
        validate="many_to_one"
    )
    
    # Check all GBD locations were successfully mapped
    if disease_burden["ISO3"].isna().any():

        missing = (
            disease_burden.loc[
                disease_burden["ISO3"].isna(),
                "location"
            ]
            .drop_duplicates()
            .sort_values()
            .tolist()
        )

        print(
            "\nWARNING: The following countries could not be mapped "
            "to ISO3 and will be excluded:"
        )
    
        for country in missing:
            print(f" - {country}")
    
        disease_burden = disease_burden[
            disease_burden["ISO3"].notna()
        ].copy()

    # Make year data types consistent 

    population["year"] = population["year"].astype(
        disease_burden["year"].dtype
    )

    time_points = np.asarray(
        time_points,
        dtype=disease_burden["year"].dtype
    )

    # Check requested years exist 

    burden_years = set(
        disease_burden["year"].unique()
    )

    population_years = set(
        population["year"].unique()
    )

    missing_burden_years = (
        set(time_points) - burden_years
    )

    missing_population_years = (
        set(time_points) - population_years
    )

    if missing_burden_years:
        raise ValueError(
            "The following requested years are missing from "
            "the disease-burden projections: "
            f"{sorted(missing_burden_years)}"
        )

    if missing_population_years:
        raise ValueError(
            "The following requested years are missing from "
            "the population projections: "
            f"{sorted(missing_population_years)}"
        )

    # Keep only requested years 

    disease_burden = disease_burden[
        disease_burden["year"].isin(time_points)
    ].copy()

    population = population[
        population["year"].isin(time_points)
    ].copy()

    # Check BAU scenarios 

    available_scenarios = sorted(
        population["scenario"]
        .dropna()
        .unique()
    )

    if bau_scenario not in available_scenarios:
        raise ValueError(
            f"BAU scenario '{bau_scenario}' was not found. "
            f"Available scenarios are: {available_scenarios}"
        )

    # Extract BAU population 

    bau_population = population.loc[
        population["scenario"] == bau_scenario,
        [
            "country",
            "year",
            "value"
        ]
    ].copy()

    bau_population = bau_population.rename(
        columns={
            "value": "population_BAU"
        }
    )

    # Check BAU population uniqueness
    duplicate_bau = bau_population.duplicated(
        subset=[
            "country",
            "year"
        ],
        keep=False
    )

    if duplicate_bau.any():
        duplicates = bau_population.loc[
            duplicate_bau,
            [
                "country",
                "year"
            ]
        ]

        raise ValueError(
            "Multiple BAU population values were found for "
            "the same country and year:\n"
            f"{duplicates}"
        )

    # Add BAU population to all scenarios 

    population = population.merge(
        bau_population,
        on=[
            "country",
            "year"
        ],
        how="left",
        validate="many_to_one"
    )

    # Calculate scaling factors

    population["population_scaling_factor"] = (
        population["value"]
        / population["population_BAU"]
    )

    population["population_scaling_factor"] = (
        population["population_scaling_factor"]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
    )

    if population["population_scaling_factor"].isna().any():

        invalid_iso3 = (
            population.loc[
                population["population_scaling_factor"].isna(),
                "country"
            ]
            .dropna()
            .unique()
            .tolist()
        )

        print(
            "\nWARNING: The following countries have incomplete "
            "population projections and will be excluded:"
        )
    
        for iso3 in sorted(invalid_iso3):
            print(f" - {iso3}")
    
        population = population[
            ~population["country"].isin(invalid_iso3)
        ].copy()
    
        disease_burden = disease_burden[
            ~disease_burden["ISO3"].isin(invalid_iso3)
        ].copy()

    # Generate one file per scenario 

    output_directory = disease_burden_path.parent

    scenario_outputs = {}

    for scenario in available_scenarios:

        print(
            f"Generating disease-burden projections for "
            f"{scenario}..."
        )

        # Scaling factor for each country-year in current scenario
        scenario_scaling = population.loc[
            population["scenario"] == scenario,
            [
                "country",
                "year",
                "population_scaling_factor"
            ]
        ].copy()

        # Apply same country-year factor to all
        # age × sex × cause combinations
        scenario_burden = disease_burden.merge(
            scenario_scaling,
            left_on=[
                "ISO3",
                "year"
            ],
            right_on=[
                "country",
                "year"
            ],
            how="left",
            validate="many_to_one"
        )

        # Check every disease-burden row was matched
        if scenario_burden[
            "population_scaling_factor"
        ].isna().any():

            missing = scenario_burden.loc[
                scenario_burden[
                    "population_scaling_factor"
                ].isna(),
                [
                    "location",
                    "year"
                ]
            ].drop_duplicates()

            raise ValueError(
                f"Population scaling factors for {scenario} "
                "could not be matched to:\n"
                f"{missing}"
            )

        # Scale disease-burden values
        scenario_burden["val"] = (
            scenario_burden["val"]
            * scenario_burden[
                "population_scaling_factor"
            ]
        )

        # Return to exact original file structure
        scenario_burden = scenario_burden[
            [
                "location",
                "sex",
                "age",
                "cause",
                "year",
                "val"
            ]
        ]

        scenario_burden = (
            scenario_burden
            .sort_values(
                by=[
                    "location",
                    "sex",
                    "age",
                    "cause",
                    "year"
                ]
            )
            .reset_index(drop=True)
        )

        # Example:
        # total_YLDs_gendered.csv
        # -> SSP1_total_YLDs_gendered.csv
        output_path = (
            output_directory
            / f"{scenario}_{disease_burden_path.name}"
        )

        scenario_burden.to_csv(
            output_path,
            index=False
        )

        print(
            f"Saved {scenario} disease-burden projections "
            f"to: {output_path}"
        )

        scenario_outputs[scenario] = scenario_burden

    return scenario_outputs