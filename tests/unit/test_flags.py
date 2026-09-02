from vroometr.flags import FLAG_AI_WRITES, is_enabled, use_in_memory_flags


def test_kill_switches_default_on() -> None:
    assert is_enabled("web_research") is True
    assert is_enabled("vision") is True
    assert is_enabled("voice") is True
    assert is_enabled(FLAG_AI_WRITES) is True


def test_kill_switch_can_be_turned_off() -> None:
    use_in_memory_flags({FLAG_AI_WRITES: False})
    assert is_enabled(FLAG_AI_WRITES) is False
    assert is_enabled("web_research") is True
