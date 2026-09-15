from b3_agent.options.identity import canonical_option_ticker


def test_canonicalizes_on_suffix():
    assert canonical_option_ticker("ABEVV153 ON") == "ABEVV153"


def test_canonicalizes_pn_suffix():
    assert canonical_option_ticker("BBDCJ213 PN") == "BBDCJ213"


def test_canonicalizes_dr1_suffix():
    assert canonical_option_ticker("XPBRJ100 DR1") == "XPBRJ100"


def test_preserves_already_canonical_ticker():
    assert canonical_option_ticker("ABEVV153") == "ABEVV153"


def test_does_not_change_unknown_suffix():
    assert canonical_option_ticker("ABEVV153 XX") == "ABEVV153 XX"


def test_normalizes_extra_whitespace():
    assert canonical_option_ticker("  ABEVV153   ON  ") == "ABEVV153"
