"""US / remote tech postings with role, location, visa, new-grad and salary columns.

The parsing rules live in the `pipeline` package (unit-tested there); this model applies
them. dbt must be run from the repo root with PYTHONPATH=. so `pipeline` is importable.
"""


def model(dbt, session):
    dbt.config(materialized="table")
    from pipeline.enrich import enrich

    return enrich(dbt.ref("stg_postings").df())
