from src.api.future_features import detect_language

def test_detect_english():
    assert detect_language("Why is this machine low risk?") == "en"

def test_detect_hindi():
    assert detect_language("यह मशीन कम जोखिम में क्यों है?") == "hi"

def test_detect_hinglish():
    assert detect_language("machine ka risk kya hai aur maintenance kya karna hai") == "hinglish"
