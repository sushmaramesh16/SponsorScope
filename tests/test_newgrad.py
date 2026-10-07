import pytest

from pipeline.newgrad import is_internship, is_new_grad, min_years_required


@pytest.mark.parametrize(
    "title",
    [
        "Software Engineer, New Grad",
        "New Graduate Data Scientist 2027",
        "Entry-Level Data Analyst",
        "Junior Backend Engineer",
        "Software Engineer I",
        "Early Career Machine Learning Engineer",
        "Associate Data Scientist",
    ],
)
def test_title_new_grad(title):
    assert is_new_grad(title, "")


@pytest.mark.parametrize(
    "title",
    [
        "Senior Software Engineer, New Grad Programs",  # senior wins
        "Staff Data Engineer",
        "Software Engineer II",
        "Engineering Manager",
        "Software Engineering Intern",  # interns are tracked separately
    ],
)
def test_title_not_new_grad(title):
    assert not is_new_grad(title, "")


@pytest.mark.parametrize(
    "desc,expected",
    [
        ("You have 0-2 years of experience in data science.", True),
        ("1+ years of professional experience with Python.", True),
        ("Up to 2 years of industry experience.", True),
        ("0 to 2 years experience building ML systems", True),
        ("We welcome recent graduates and new grads.", True),
        ("2+ years of experience required.", False),
        ("5+ years of experience in backend development; 1+ years with Kubernetes.", False),
        ("At least 3 years of experience shipping production code.", False),
        ("A strong engineer with great communication skills.", False),
    ],
)
def test_description(desc, expected):
    assert is_new_grad("Data Scientist", desc) is expected


def test_years_ignores_non_experience_numbers():
    assert min_years_required("We have been around for 10 years and offer 4 weeks PTO.") is None
    assert min_years_required("3+ years of experience") == 3


def test_internship():
    assert is_internship("Data Science Intern, Summer 2027")
    assert is_internship("Software Engineering Co-op")
    assert not is_internship("Internal Tools Engineer")
