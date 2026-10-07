select job_key, cast(first_seen as date) as first_seen, cast(last_seen as date) as last_seen
from {{ source('raw', 'postings_seen') }}
