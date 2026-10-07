select company_name, lca_employer_name
from {{ source('raw', 'employer_aliases') }}
