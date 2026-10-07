-- Open US / remote tech postings, one row per opening, with employer H-1B context.
select
    d.job_key,
    d.snapshot_date,
    d.ats,
    d.company_name,
    d.title,
    d.role,
    d.role_group,
    d.department,
    d.location_raw,
    d.city,
    d.state,
    d.is_remote,
    coalesce(cast(d.posted_at as date), h.first_seen) as posted_date,
    h.first_seen,
    h.last_seen,
    d.apply_url,
    d.salary_min,
    d.salary_max,
    d.salary_interval,
    d.visa_status,
    d.is_new_grad,
    d.is_internship,
    d.min_years_experience,
    d.duplicate_count,
    c.employer_norm,
    c.match_method,
    c.lca_certified,
    c.lca_median_wage as lca_company_median_wage,
    r.lca_certified as lca_role_certified,
    r.lca_median_wage as lca_role_median_wage
from {{ ref('int_postings_deduped') }} d
join {{ ref('fct_postings_history') }} h using (job_key)
left join {{ ref('dim_companies') }} c using (company_name)
left join {{ ref('stg_lca_employer_roles') }} r
    on r.employer_norm = c.employer_norm and r.role = d.role
