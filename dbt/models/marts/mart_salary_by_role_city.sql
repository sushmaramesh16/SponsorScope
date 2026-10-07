-- Posted pay (annualized midpoint) by role and metro. Remote postings get their own bucket.
with j as (
    select
        role,
        case when is_remote and city is null then 'Remote (US)'
             when city is not null then city || ', ' || state
             else 'Unspecified US' end as metro,
        (salary_min + salary_max) / 2 as salary_mid
    from {{ ref('fct_jobs') }}
    where salary_min is not null and not is_internship
)

select
    role,
    metro,
    count(*) as postings_with_salary,
    round(median(salary_mid)) as median_posted_salary,
    round(quantile_cont(salary_mid, 0.25)) as p25_posted_salary,
    round(quantile_cont(salary_mid, 0.75)) as p75_posted_salary
from j
group by 1, 2
