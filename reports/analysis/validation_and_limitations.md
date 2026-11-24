# Project Validation and Identified Limitations

## 1. Overview

The first validation phase of the Pharmacy Stock Optimization & Historical Monitoring System has confirmed that the main inventory analysis components are working correctly. The classification visualisations have been generated and inspected, and the existing automated test suite has completed successfully.

However, the validation process also identified a limitation in the pharmaceutical ATC5 enrichment methodology. This issue will be addressed in a future development phase.

## 2. Automated testing

The existing test suite was executed using `python -m pytest -v`.

All **13 tests passed successfully**, with an **execution time of 1.38 seconds**. The tests cover inventory calculations, discrepancy analysis, CSV loading, product scope comparisons, data transformations and stock validation.

These results provide confidence in the existing inventory processing modules. Nevertheless, the newer billing, demand classification, ATC enrichment and visualisation scripts are not yet comprehensively covered by automated tests. Additional tests should be introduced progressively as the project develops.

## 3. ATC5 enrichment limitation

The ATC5 enrichment process initially used two official French pharmaceutical reference files :

- `CIS_CIP_bdpm.txt`, providing the relationship between CIP13 presentation codes and CIS identifiers.
- `CIS_MITM.txt`, providing ATC information for medicines classified as medicines of major therapeutic interest (*médicaments d'intérêt thérapeutique majeur*).

The initial enrichment successfully matched **549 of the 699 monitored products**, corresponding to **78.54% coverage**.

An audit of the remaining 150 products showed that their CIP13 identifiers were present in the CIP reference file, but their associated CIS identifiers were absent from the MITM file.

The investigation revealed an **important methodological limitation** : the MITM reference is a specialised list and **does not represent the complete French pharmaceutical market**. Consequently, the **150 unmatched products cannot be considered** medicines without an ATC classification.

The current matching rate therefore represents coverage by the MITM reference, not overall ATC5 availability.

## 4. Potential future improvements

This limitation can be addressed in a future version by using a broader pharmaceutical reference dataset.

The existing MITM reference can also be retained as a separate indicator of medicines of major therapeutic interest.

## 5. Conclusion and development decision

The first validation phase has demonstrated that the main inventory analysis pipeline is operational and that all 13 existing automated tests pass.

The project will therefore proceed without attempting to achieve perfect pharmaceutical reference coverage at this stage.

The priority is to complete the analytical framework, strengthen automated testing, document the methodology and translate the classification results into practical inventory management insights.
