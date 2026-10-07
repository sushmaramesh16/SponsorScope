from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RAW_POSTINGS = RAW / "postings"
RAW_LCA = RAW / "lca"
SEEDS = ROOT / "seeds"
APP_DATA = DATA / "app"
HISTORY = DATA / "history"
WAREHOUSE = DATA / "sponsorscope.duckdb"

CANDIDATES_CSV = SEEDS / "candidate_companies.csv"
COMPANIES_CSV = SEEDS / "companies.csv"
ALIASES_CSV = SEEDS / "employer_aliases.csv"
LCA_EMPLOYERS = DATA / "lca" / "lca_employers.parquet"
LCA_EMPLOYER_ROLES = DATA / "lca" / "lca_employer_roles.parquet"
LCA_META = DATA / "lca" / "lca_meta.json"
SEEN_HISTORY = HISTORY / "postings_seen.parquet"
