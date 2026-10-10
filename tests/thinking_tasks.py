"""Public, synthetic coding tasks with fixed independent acceptance checks."""
from dataclasses import dataclass
from textwrap import dedent


@dataclass(frozen=True)
class Task:
    name: str
    prompt: str
    files: dict[str, str]
    checks: str


TASKS = (
    Task(
        "env-parser",
        "Fix parse_env in envfile.py. Ignore blank lines and full-line comments. "
        "Accept ASCII shell-variable keys with surrounding whitespace. Split assignments "
        "only at the first equals sign, preserve equals signs and hash characters inside "
        "values, and remove only one matching pair of outer single or double quotes. "
        "Reject missing equals signs, invalid keys, and unmatched outer quotes with "
        "ValueError. Empty values are valid and the last duplicate key wins. Values are "
        "literal: do not interpolate or execute anything. Read the files, make the "
        "smallest correct change, run python checks.py without modifying it, and summarize.",
        {"envfile.py": dedent('''\
            def parse_env(text):
                result = {}
                for line in text.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    key, value = line.split("=")
                    result[key.strip()] = value.strip().strip("\\\"'")
                return result
        ''')},
        dedent('''\
            from envfile import parse_env
            assert parse_env("\\n # comment\\n A = plain \\n") == {"A": "plain"}
            assert parse_env("URL=https://example.test/?a=b#fragment") == {"URL": "https://example.test/?a=b#fragment"}
            assert parse_env('A="  spaced = # literal  "') == {"A": "  spaced = # literal  "}
            assert parse_env("A='literal $HOME'") == {"A": "literal $HOME"}
            assert parse_env("A=\\\"'inner'\\\"") == {"A": "'inner'"}
            assert parse_env("_NAME2=\\n_NAME2=last") == {"_NAME2": "last"}
            assert parse_env("EMPTY=") == {"EMPTY": ""}
            assert parse_env("Q=''\\nD=\\\"\\\"") == {"Q": "", "D": ""}
            for invalid in ("missing", "1KEY=x", "BAD-KEY=x", "=x", "é=x", "A='unterminated", 'A="mismatch\\\''):
                try:
                    parse_env(invalid)
                except ValueError:
                    pass
                else:
                    raise AssertionError(invalid)
            print("env-parser checks passed")
        '''),
    ),
    Task(
        "csv-filter",
        "Add --min-seconds to the CSV summarizer CLI and a matching min_seconds argument "
        "to summarize. Default is zero and existing output stays compatible. Include "
        "rows whose seconds are greater than or equal to the threshold, grouped by "
        "engine and sorted by engine name. Reject negative or non-finite thresholds "
        "and durations, and negative or non-integer token counts. Validation must also "
        "apply to rows that would be filtered out. On invalid input the CLI must exit "
        "nonzero, write a useful error to stderr without a traceback, and emit no partial "
        "JSON to stdout. Read the files, make the smallest correct change, run python "
        "checks.py without modifying it, and summarize.",
        {
            "summary.py": dedent('''\
                import csv
                import io

                def summarize(text):
                    groups = {}
                    for row in csv.DictReader(io.StringIO(text)):
                        group = groups.setdefault(row["engine"], {"requests": 0, "tokens": 0})
                        group["requests"] += 1
                        group["tokens"] += int(row["tokens"])
                    return dict(sorted(groups.items()))
            '''),
            "cli.py": dedent('''\
                import argparse
                import json
                import sys
                from summary import summarize

                def main():
                    parser = argparse.ArgumentParser()
                    parser.parse_args()
                    print(json.dumps(summarize(sys.stdin.read()), sort_keys=True))

                if __name__ == "__main__":
                    main()
            '''),
        },
        dedent('''\
            import json
            import subprocess
            import sys
            from summary import summarize
            text = "engine,seconds,tokens\\ngufo,1,10\\nhalogen,2,20\\ngufo,3,30\\n"
            expected = {"gufo": {"requests": 2, "tokens": 40}, "halogen": {"requests": 1, "tokens": 20}}
            assert summarize(text) == expected
            assert list(summarize(text)) == ["gufo", "halogen"]
            assert summarize(text, min_seconds=2) == {"gufo": {"requests": 1, "tokens": 30}, "halogen": {"requests": 1, "tokens": 20}}
            assert summarize(text, min_seconds=4) == {}
            for threshold in (-1, float("inf"), float("nan")):
                try:
                    summarize(text, min_seconds=threshold)
                except ValueError:
                    pass
                else:
                    raise AssertionError(threshold)
            for row in ("gufo,-1,1", "gufo,nan,1", "gufo,inf,1", "gufo,1,-1", "gufo,1,1.5"):
                try:
                    summarize("engine,seconds,tokens\\n" + row + "\\n", min_seconds=100)
                except ValueError:
                    pass
                else:
                    raise AssertionError(row)
            def cli(args, data):
                return subprocess.run([sys.executable, "cli.py", *args], input=data, text=True, capture_output=True)
            result = cli([], text)
            assert result.returncode == 0 and json.loads(result.stdout) == expected
            result = cli(["--min-seconds", "2"], text)
            assert result.returncode == 0 and json.loads(result.stdout) == summarize(text, min_seconds=2)
            for args, data in ((["--min-seconds", "-1"], text), (["--min-seconds", "nan"], text),
                               ([], text + "gufo,1,-1\\n"), (["--min-seconds", "100"], text + "gufo,-1,0\\n")):
                result = cli(args, data)
                assert result.returncode != 0 and result.stderr and not result.stdout
                assert "Traceback" not in result.stderr
            print("csv-filter checks passed")
        '''),
    ),
)
