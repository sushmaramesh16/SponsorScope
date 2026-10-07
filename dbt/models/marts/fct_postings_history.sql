-- first_seen / last_seen per in-scope posting, accumulated across daily runs.
-- Previous history comes from the committed data/history/postings_seen.parquet, which
-- pipeline.export rewrites from this model after every run.
with today as (
    select job_key, snapshot_date as first_seen, snapshot_date as last_seen
    from {{ ref('int_postings_enriched') }}
),

prev as (
    select job_key, first_seen, last_seen from {{ ref('stg_postings_seen') }}
),

unioned as (
    select * from prev
    union all
    select * from today
)

select
    job_key,
    min(first_seen) as first_seen,
    max(last_seen) as last_seen,
    max(last_seen) = (select max(snapshot_date) from {{ ref('stg_postings') }}) as is_open
from unioned
group by job_key
