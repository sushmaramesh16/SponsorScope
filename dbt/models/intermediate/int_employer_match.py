"""One row per job-board company: the matched LCA employer (normalized name) and how."""


def model(dbt, session):
    dbt.config(materialized="table")
    import pandas as pd

    from pipeline.employer_match import match_companies

    companies = dbt.ref("stg_companies").df()
    aliases = dbt.ref("stg_employer_aliases").df()
    employers = dbt.ref("stg_lca_employers").df()
    matches = match_companies(
        companies["company_name"],
        employers["employer_norm"],
        dict(zip(aliases["company_name"], aliases["lca_employer_name"], strict=True)),
    )
    return pd.DataFrame(
        {
            "company_name": [m.company for m in matches],
            "employer_norm": [m.employer_norm for m in matches],
            "match_method": [m.method for m in matches],
            "match_score": [m.score for m in matches],
        }
    )
