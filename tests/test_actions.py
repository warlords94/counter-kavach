import pytest

from kavach import actions


@pytest.mark.parametrize("level", ["LOW", "MEDIUM", "HIGH"])
@pytest.mark.parametrize("lang", ["en", "hi"])
def test_every_level_has_actions_in_both_languages(level, lang):
    assert actions.recommended(level, lang)


def test_high_actions_include_reporting_channels():
    text = " ".join(actions.recommended("HIGH", "en"))
    assert "1930" in text and "cybercrime.gov.in" in text


def test_digital_arrest_high_message_matches_plan_wording():
    msg = actions.customer_message("digital_arrest", "HIGH", "en")
    assert msg.startswith("You are safe here.")
    assert "वीडियो कॉल पर गिरफ्तार नहीं करती" in actions.customer_message("digital_arrest", "HIGH", "hi")


@pytest.mark.parametrize("scam_type", ["digital_arrest", "investment", "kyc_or_account_block",
                                       "relative_in_trouble", "lottery_or_refund", "other", "none_detected"])
@pytest.mark.parametrize("level", ["LOW", "MEDIUM", "HIGH"])
@pytest.mark.parametrize("lang", ["en", "hi"])
def test_customer_messages_exist_and_are_short(scam_type, level, lang):
    msg = actions.customer_message(scam_type, level, lang)
    assert msg and len(msg.split()) <= 40


def test_low_level_gets_awareness_note_whatever_the_type():
    assert actions.customer_message("investment", "LOW", "en") == actions.customer_message("none_detected", "LOW", "en")


def test_action_options_include_proceed_and_escalate():
    opts = actions.action_options()
    assert any("Proceed" in o for o in opts) and any("manager" in o.lower() for o in opts)
