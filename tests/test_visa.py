import pytest

from pipeline.visa import NO, NONE, YES, classify_visa_language

NEGATIVE = [
    "We are unable to sponsor visas for this position.",
    "Please note: we are unable to sponsor or take over sponsorship of an employment visa at this time.",
    "This role is not eligible for visa sponsorship.",
    "Visa sponsorship is not available for this role.",
    "No visa sponsorship is available.",  # contains "sponsorship is available" - negation must win
    "We will not sponsor H-1B visas for this opening.",
    "Company X does not offer sponsorship.",
    "We cannot sponsor work visas now or in the future.",
    "Applicants must be authorized to work in the U.S. without the need for current or future visa sponsorship.",
    "Candidates must have authorization to work in the United States without requiring sponsorship now or in the future.",
    "Candidates who now or in the future require sponsorship will not be considered.",
    "Must be a U.S. citizen.",
    "U.S. citizenship is required for this position.",
    "This position requires an active Top Secret security clearance.",
    "Visa sponsorship: No",
    "We don't sponsor visas at this time.",
    "Please note the Company may not be able to employ candidates who have United States work "
    "authorization related to certain U.S. visa categories, or support future H-1B sponsorship at this time.",
]

POSITIVE = [
    "We do sponsor and take over sponsorship of employment visas for this role.",
    "Visa sponsorship is available for this position.",
    "Sponsorship is available for this position and other select roles.",
    "We sponsor H-1B visas and support green card applications.",
    "We are open to sponsoring candidates who need a visa.",
    "H-1B transfers are welcome.",
    "We offer visa sponsorship for qualified candidates.",
    "Visa sponsorship: Yes",
    "Relocation support and visa sponsorship where applicable",
    "Visa sponsorship may be available for this role.",
    # a hedge limits the refusal to other roles, so the positive statement stands
    "Visa sponsorship: We do sponsor visas! However, we aren't able to successfully sponsor visas "
    "for every role and every candidate.",
]

NOT_MENTIONED = [
    "",
    None,
    "Join our team building data pipelines in Python and SQL.",
    # EEO boilerplate mentions citizenship but is not a requirement
    "We consider all applicants without regard to race, color, religion, national origin, or citizenship status.",
    # application-form questions are not policy
    "Will you now or in the future require sponsorship for employment visa status?",
    "Do you require visa sponsorship?",
    "Finally, a company sponsored 401(k) retirement plan.",
    "We are a proud sponsor of local hackathons.",
    "Ability to obtain a security clearance desired.",
    "Ensure compliance with export laws without sponsorship for an export license.",
    "Must be authorized to work in the United States.",
]


@pytest.mark.parametrize("text", NEGATIVE)
def test_negative(text):
    assert classify_visa_language(text) == NO


@pytest.mark.parametrize("text", POSITIVE)
def test_positive(text):
    assert classify_visa_language(text) == YES


@pytest.mark.parametrize("text", NOT_MENTIONED)
def test_not_mentioned(text):
    assert classify_visa_language(text) == NONE


def test_negative_beats_positive_across_sentences():
    text = "We sponsor visas for many roles. Unfortunately, we cannot sponsor for this position."
    assert classify_visa_language(text) == NO


def test_relevant_sentence_inside_long_description():
    text = (
        "About us\nWe build things.\n\nRequirements\n- 3+ years of Python\n"
        "- You must be legally authorized to work in the US without sponsorship\n\nBenefits\n- 401k"
    )
    assert classify_visa_language(text) == NO
