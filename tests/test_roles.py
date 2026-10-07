import pytest

from pipeline.roles import ROLE_GROUP, ROLES, normalize_role


@pytest.mark.parametrize(
    "title,role",
    [
        ("Senior Data Scientist", "Data Scientist"),
        ("Data Scientist, AI", "Data Scientist"),
        ("Data Engineer, ML Platform", "Data Engineer"),
        ("Machine Learning Engineer", "ML Engineer"),
        ("Senior MLE, Ranking", "ML Engineer"),
        ("Applied AI Engineer", "AI Engineer"),
        ("LLM Engineer", "AI Engineer"),
        ("Research Scientist, Reinforcement Learning", "Research Scientist"),
        ("Research Engineer, ML", "Research Scientist"),
        ("Product Analyst", "Data Analyst"),
        ("Business Intelligence Analyst", "Data Analyst"),
        ("Analytics Engineer", "Analytics Engineer"),
        ("Software Engineer", "Software Engineer"),
        ("Staff Software Engineer, Payments", "Software Engineer"),
        ("Software Engineer II, Backend (Streaming)", "Backend Engineer"),
        ("Backend Engineer (Go)", "Backend Engineer"),
        ("Frontend Engineer", "Frontend Engineer"),
        ("Senior Full Stack Engineer (React)", "Full-Stack Engineer"),
        ("iOS Engineer", "Mobile Engineer"),
        ("Site Reliability Engineer", "Platform / DevOps / SRE"),
        ("Member of Technical Staff", "Software Engineer"),
    ],
)
def test_roles(title, role):
    assert normalize_role(title) == role


@pytest.mark.parametrize(
    "title",
    [
        "Engineering Manager, Data Platform",
        "Director of Data Science",
        "Solutions Engineer",
        "Account Executive",
        "Mechanical Engineer",
        "Firmware Engineer",
        "Product Designer",
        "Technical Recruiter",
        "Financial Analyst",
        "",
        None,
    ],
)
def test_out_of_scope(title):
    assert normalize_role(title) is None


def test_every_role_has_group():
    assert set(ROLE_GROUP) == set(ROLES)


@pytest.mark.parametrize(
    "title",
    [
        "Senior ASIC RTL Design Engineer, AI Hardware",
        "Systems Safety Engineer, Command & Control (C2)",
        "Senior Systems Engineer, Maritime",
        "IT Systems Engineer, Client Platform Engineer, macOS",
        "Network Engineer",
    ],
)
def test_hardware_and_it_titles_out_of_scope(title):
    assert normalize_role(title) is None


@pytest.mark.parametrize(
    "title,role",
    [
        ("Mission Software Engineer, Mission Systems, Cyber Security", "Software Engineer"),
        ("Software Engineer in Test", "Software Engineer"),
        ("Machine Learning Engineer, Neural Network Compression", "ML Engineer"),
        ("Data Quality Engineer", "Data Engineer"),
    ],
)
def test_software_titles_with_hardware_words(title, role):
    assert normalize_role(title) == role
