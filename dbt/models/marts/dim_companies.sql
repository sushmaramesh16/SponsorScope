with open_jobs as (
    select company_name, count(*) as open_postings
    from {{ ref('int_postings_deduped') }}
    group by 1
)

select
    c.company_name,
    c.ats,
    c.board_token,
    m.employer_norm,
    m.match_method,
    m.match_score,
    e.employer_name as lca_employer_name,
    coalesce(e.lca_filings, 0) as lca_filings,
    coalesce(e.lca_certified, 0) as lca_certified,
    coalesce(e.lca_denied, 0) as lca_denied,
    coalesce(e.lca_tech_certified, 0) as lca_tech_certified,
    e.lca_median_wage,
    e.lca_n_states,
    e.lca_top_titles,
    e.lca_top_states,
    coalesce(o.open_postings, 0) as open_postings
from {{ ref('stg_companies') }} c
left join {{ ref('int_employer_match') }} m using (company_name)
left join {{ ref('stg_lca_employers') }} e on e.employer_norm = m.employer_norm
left join open_jobs o using (company_name)
