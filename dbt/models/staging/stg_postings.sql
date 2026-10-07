-- Latest snapshot only, one row per board posting.
with snap as (
    select *
    from {{ source('raw', 'postings_snapshots') }}
    where snapshot_date = (select max(snapshot_date) from {{ source('raw', 'postings_snapshots') }})
)

select
    ats || ':' || board_token || ':' || job_id as job_key,
    cast(snapshot_date as date) as snapshot_date,
    ats,
    board_token,
    company_name,
    job_id,
    trim(title) as title,
    location_raw,
    country_hint,
    remote_hint,
    department,
    employment_type,
    try_cast(posted_at as timestamptz) as posted_at,
    apply_url,
    description,
    pay_min,
    pay_max,
    upper(pay_currency) as pay_currency,
    pay_interval,
    try_cast(fetched_at as timestamptz) as fetched_at
from snap
qualify row_number() over (partition by ats, board_token, job_id order by fetched_at desc) = 1
