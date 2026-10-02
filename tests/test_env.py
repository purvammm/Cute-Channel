import re

from pipeline import credentials, env, paths


def test_parse_env_text_handles_comments_quotes_and_export():
    text = """
# a comment
PLAIN=value
export EXPORTED=yes
QUOTED="has # hash and spaces"
SINGLE='single'
INLINE=abc # trailing comment
NOSPACE=abc#def
EMPTY=
not a valid line
9BAD=x
"""
    assert env.parse_env_text(text) == {
        "PLAIN": "value",
        "EXPORTED": "yes",
        "QUOTED": "has # hash and spaces",
        "SINGLE": "single",
        "INLINE": "abc",
        "NOSPACE": "abc#def",
        "EMPTY": "",
    }


def test_load_env_file_missing_is_empty(tmp_path):
    assert env.load_env_file(tmp_path / "nope.env") == {}


def test_real_environment_overrides_env_file():
    merged = env.merged_settings({"A": "from-env", "B": ""}, {"A": "from-file", "B": "file-b"})
    assert merged == {"A": "from-env", "B": "file-b"}  # empty env vars don't erase file values


def test_versions_file_is_consistent():
    versions = env.load_versions()
    assert versions["BLENDER_VERSION"].startswith(versions["BLENDER_SERIES"] + ".")
    assert versions["BLENDER_INTEL_MAC_VERSION"].startswith(
        versions["BLENDER_INTEL_MAC_SERIES"] + "."
    )
    for key, value in versions.items():
        if key.endswith("SHA256"):
            assert re.fullmatch(r"[0-9a-f]{64}", value), key
    assert all(m.startswith("https://") for m in versions["BLENDER_MIRRORS"].split())


def test_env_example_lists_exactly_the_known_keys():
    example = env.parse_env_text(paths.ENV_EXAMPLE_FILE.read_text(encoding="utf-8"))
    assert set(example) == credentials.all_keys()
    assert all(value == "" for value in example.values()), ".env.example must not hold values"
