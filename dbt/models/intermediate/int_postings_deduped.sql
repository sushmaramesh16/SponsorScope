-- The same opening is sometimes posted more than once on a board (identical company,
-- title and location). Keep the most recently posted copy and count the duplicates.
select * exclude (rn)
from (
    select
        *,
        count(*) over (
            partition by company_name, lower(title), coalesce(location_raw, '')
        ) as duplicate_count,
        row_number() over (
            partition by company_name, lower(title), coalesce(location_raw, '')
            order by posted_at desc nulls last, job_key
        ) as rn
    from {{ ref('int_postings_enriched') }}
)
where rn = 1
