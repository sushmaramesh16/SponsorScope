select * from {{ ref('fct_jobs') }}
where salary_min > salary_max or salary_min < 20000 or salary_max > 2000000
