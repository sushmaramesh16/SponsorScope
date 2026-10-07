select
    ats,
    token as board_token,
    company_name,
    try_cast(open_postings_at_verify as integer) as open_postings_at_verify
from {{ source('raw', 'companies') }}
