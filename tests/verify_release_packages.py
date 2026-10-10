"""Fail closed if production math/frontend folders are mixed or incomplete."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATH = ROOT / "release" / "math"
FRONT = ROOT / "release" / "frontend"

def require(path):
    assert path.is_file() and path.stat().st_size > 0, f"Missing/empty: {path}"
    return path

def main():
    for name in ("index.html", "style.css", "game.js", "money.js", "rgs.js", "game_config.json"):
        require(FRONT / name)
    assets = FRONT / "assets"
    assert assets.is_dir() and any(p.is_file() for p in assets.rglob("*")), "Missing frontend assets"
    for pattern in ("books_*.json", "books_*.jsonl*", "lookUpTable_*.csv"):
        assert not list(FRONT.glob(pattern)), f"Production frontend contains local outcomes: {pattern}"
    html = (FRONT / "index.html").read_text()
    for name in ("style.css", "game.js", "money.js", "rgs.js"):
        assert name in html, f"Frontend does not reference {name}"
    config = json.loads(require(FRONT / "game_config.json").read_text())
    assert config["requiresRGS"] is True, "Production frontend must require RGS"
    assert len(config["betLevels"]) == 13, "Expected 13 bet levels"
    assert config["payoutUnit"] == "100 = 1.0x ordinary bet"
    index = json.loads(require(MATH / "index.json").read_text())
    assert {m["name"] for m in index["modes"]} == {"base", "bonus"}
    for mode in index["modes"]:
        name = mode["name"]
        assert mode["events"] == f"books_{name}.jsonl.zst"
        assert mode["weights"] == f"lookUpTable_{name}.csv"
        require(MATH / mode["events"])
        lut = require(MATH / mode["weights"])
        with lut.open(newline="") as stream:
            rows = csv.reader(stream)
            first = next(rows, None)
            assert first and len(first) == 3 and all(int(v) >= 0 for v in first), f"Invalid LUT: {lut}"
        assert config["modes"][name]["books"] >= 100000
    for name in ("math_summary.json", "replay_ids.json", "validation_report.json", "four_million_report.json"):
        require(MATH / name)
    summary = json.loads((MATH / "math_summary.json").read_text())
    assert summary == config, "Math/frontend configuration mismatch"
    report = json.loads((MATH / "four_million_report.json").read_text())
    assert report["total_rounds"] == 104000000
    assert len(report["results"]) == 26
    assert len({(r["mode"], r["bet_micros"]) for r in report["results"]}) == 26
    assert all(r["rounds"] == 4000000 and r["pass_checks"] and r["precision_errors"] == 0 for r in report["results"])
    print("PASS independent production packages: 2 modes, 13 bets, 104,000,000 verified rounds")

if __name__ == "__main__":
    main()
