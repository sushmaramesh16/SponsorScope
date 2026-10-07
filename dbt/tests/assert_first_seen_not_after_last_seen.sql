select * from {{ ref('fct_postings_history') }} where first_seen > last_seen
