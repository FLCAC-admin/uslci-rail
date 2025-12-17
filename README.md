# uslci-rail
Calculation of U.S. average train transport processes. 

# How to use
Required for environment:
- [flcac-utils](https://github.com/FLCAC-admin/flcac-utils)
  - pip install git+https://github.com/FLCAC-admin/flcac-utils.git
- [esupy](https://github.com/USEPA/esupy/tree/e0464c50701001501ba7bc71a608a26ebc0c2688)
  - pip install git+https://github.com/USEPA/esupy.git

Run [build_rail_transportation_olca_objects.py](build_rail_transportation_olca_objects.py)

Import the zip file created in the output folder into openLCA 2.x.x. The dataset
needs to be imported into a database containing USLCI so that default providers are linked.

## Datasets

| Datasts             | Version | flcac-utils | Release        |
|---------------------|---------|-------------|----------------|
| Class 1 U.S. Rail   | v1.0.0  | v0.2.2      | 2025 Q4, USLCI |
