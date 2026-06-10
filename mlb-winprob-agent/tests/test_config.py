import textwrap

import pytest

from agent.config import Config, load_config


def write(tmp_path, body):
    p = tmp_path / "c.yaml"
    p.write_text(textwrap.dedent(body))
    return p


def test_defaults_valid():
    cfg = Config()
    assert cfg.mode == "paper"
    assert cfg.signal.entry_threshold > cfg.signal.exit_threshold


def test_hysteresis_enforced(tmp_path):
    p = write(tmp_path, """
        signal:
          entry_threshold: 0.01
          exit_threshold: 0.02
    """)
    with pytest.raises(ValueError, match="entry_threshold"):
        load_config(p)


def test_unknown_key_rejected(tmp_path):
    p = write(tmp_path, """
        signal:
          bogus_key: 5
    """)
    with pytest.raises(Exception):
        load_config(p)


def test_unknown_top_level_rejected(tmp_path):
    p = write(tmp_path, """
        totally_unknown: true
    """)
    with pytest.raises(Exception):
        load_config(p)


def test_real_config_loads():
    cfg = load_config("config.yaml")
    assert cfg.signal.entry_threshold > cfg.signal.exit_threshold
    assert cfg.mode in ("paper", "live")
