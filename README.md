# MAgPIE Dietary Risk Module 

## Overview 

The **MAgPIE Dietary Risk Module** is a Python-based comparative risk assessment model that links changes in food intake from the [food demand module](https://rse.pik-potsdam.de/doc/magpie/4.6.0/15_food.htm) of the Model of Agricultural Production and its Impact on the Environment [MAgPIE](https://www.pik-potsdam.de/en/institute/departments/activities/land-use-modelling/magpie) (1) with dietary-risk exposures, relative-risk functions, and theoretical minimum risk exposure levels (TMRELs) from an emulator of the Global Burden of Disease (GBD) Diet–NCD model (2). This emulator [GBD Diet-NCD Emulator](https://github.com/shaun-solomon/GBD-Diet-NCD-Model-Emulator) estimates the burden of non-communicable diseases attributable to suboptimal diets.

For documentation of the emulator, validation results, and further information on its analytical capabilities, refer to [Additional Information](https://github.com/shaun-solomon/GBD-Diet-NCD-Model-Emulator/tree/main/Additional%20Information). 

This module translates scenario-specific changes in food intake into changes in dietary risk exposure and estimates the associated burden of disease across countries, age groups, sexes, years, and scenarios. Health outcomes are quantified using disability-adjusted life years (DALYs). 

This repository contains the model code, the required directory structure for model inputs and outputs, and a user guide. The full input dataset is distributed separately through Zenodo and must be downloaded before the model can be run. 

## Technical Documentation 

Two complementary documentation resources are provided for the MAgPIE Dietary Risk Module:

- **Technical Reference** - A web-based technical reference descrbing the soft-coupling between the modules, inputs, outputs, assumptions, calculations and analytical worflow. [View technical documentation](Add GitHub page link)

- **User Guide** - a PDF guide providing step-by-step instructions for running the module. The guide covers software requirements, repository setup, required input file structures, command-line execution, optional narrative adjustments, disease-burden projections, model outputs and a pre-run checklist. Refer to *MAgPIE_Dietary_Module_User_Guide.pdf* in the *Supplementary Information* folder in the repository.  

Users interested in the underlying methodology should refer to the technical documentation, while users primarily interested in running the module should begin with the user guide.

## Data Access 

The full set of input data required to run the MAgPIE Dietary Risk Module is distributed separately through a Zenodo repository.

The GitHub repository contains a **stub `Data` directory** only. This preserves the directory structure expected by the model while avoiding duplication of the underlying datasets in GitHub.

Before running the model:

1. Download the complete data archive from Zenodo: [add Zenodo link].
2. Extract the archive.
3. Replace the existing stub `Data` directory in the GitHub repository with the extracted `Data` directory.
4. Preserve the directory structure and file names exactly as provided.

The model uses relative paths from the `Code` directory, so the final repository structure should retain:

```text
<repository-root>/
├── Code/
├── Data/
└── Supplementary_Material/
```

## Contact 

For questions regarding the module, or to request access to the private code repository and associated data, please contact:

**Shaun Solomon**  
Research Programmer and Data Analyst for Food System Economic Cost Modelling 
Food Systems Transformation Group
Environmental Change Institute, University of Oxford  
Email: shaun.solomon@ouce.ox.ac.uk 

## Citation

Please cite the module and associated work when using this repository or derivative outputs. A suggested format and BibTeX has been provided in the repository’s CITATION.cff. Also cite the GBD methodology and any specific IHME data products used.

## References 

1. Dietrich, J. P., Bodirsky, B. L., Weindl, I., Humpenöder, F., Stevanovic, M., Rein, P., Lotze-Campen, H., & Popp, A. (2026). MAgPIE – An Open Source land-use modeling framework (Version 4.14.1). Zenodo. https://doi.org/10.5281/zenodo.1418752
2. Afshin A. et al. The Lancet (2019). Health effects of dietary risks in 195 countries, 1990–2017.