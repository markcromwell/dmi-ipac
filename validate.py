#!/usr/bin/env python3
"""DMI-IPAC validation gate.

Verifies repository structure, enforces the proprietary-isolation rule that
keeps calculation logic out of public/, and runs the unit test suite.
Exits 0 on success, non-zero on failure.
"""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))

REQUIRED_FILES = [
    "ARCHITECTURE.md",
    "validate.py",
    "netlify.toml",
    "README.md",
    "public/index.html",
    "public/app.js",
    "public/pdf.js",
    "public/styles.css",
    "netlify/functions/calculate.py",
    "tests/__init__.py",
    "tests/test_calculate.py",
    "tests/fixtures/reference_w0230.json",
]

REQUIRED_DIRS = [
    "public",
    "netlify",
    "netlify/functions",
    "tests",
    "tests/fixtures",
]

FORBIDDEN_TOKENS_IN_PUBLIC = [
    "bell_delaware",
    "belldelaware",
    "dittus_boelter",
    "dittusboelter",
    "reynolds",
    "prandtl",
    "nusselt",
]

ARCH_REQUIRED_SECTIONS = [
    "## 1. Topology",
    "## 2. Directory Layout",
    "## 3. Backend Module Contract",
    "## 4. Frontend Module Contract",
    "## 5. Wire Contract",
    "## 6. Reference Case",
    "## 7. Build, Test, Deploy Tooling",
    "## 8. Hard Architectural Rules",
]


def _ok(msg):
    print("[OK] " + msg)


def _fail(msg):
    print("[FAIL] " + msg)


def check_required_dirs():
    missing = [d for d in REQUIRED_DIRS if not os.path.isdir(os.path.join(ROOT, d))]
    if missing:
        _fail("missing required directories:")
        for d in missing:
            print("   - " + d)
        return False
    _ok("all required directories present")
    return True


def check_required_files():
    missing = [p for p in REQUIRED_FILES if not os.path.isfile(os.path.join(ROOT, p))]
    if missing:
        _fail("missing required files:")
        for p in missing:
            print("   - " + p)
        return False
    _ok("all required files present")
    return True


def check_architecture_sections():
    path = os.path.join(ROOT, "ARCHITECTURE.md")
    if not os.path.isfile(path):
        _fail("ARCHITECTURE.md missing")
        return False
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    missing = [s for s in ARCH_REQUIRED_SECTIONS if s not in text]
    if missing:
        _fail("ARCHITECTURE.md missing required sections:")
        for s in missing:
            print("   - " + s)
        return False
    _ok("ARCHITECTURE.md has all required sections")
    return True


def check_proprietary_isolation():
    public_dir = os.path.join(ROOT, "public")
    if not os.path.isdir(public_dir):
        _fail("public/ directory missing")
        return False
    violations = []
    for dirpath, _, filenames in os.walk(public_dir):
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
            except OSError:
                continue
            for token in FORBIDDEN_TOKENS_IN_PUBLIC:
                if token in content:
                    violations.append((path, token))
    if violations:
        _fail("PROPRIETARY ISOLATION VIOLATIONS in public/:")
        for path, tok in violations:
            print("   - " + path + " contains forbidden token: " + tok)
        return False
    _ok("no proprietary tokens leaked into public/")
    return True


def check_single_calc_file():
    fn_dir = os.path.join(ROOT, "netlify", "functions")
    if not os.path.isdir(fn_dir):
        _fail("netlify/functions directory missing")
        return False
    py_files = [f for f in os.listdir(fn_dir) if f.endswith(".py")]
    if py_files != ["calculate.py"]:
        _fail("netlify/functions/ must contain exactly one file: calculate.py")
        print("   - found: " + repr(py_files))
        return False
    _ok("netlify/functions/calculate.py is the sole backend file")
    return True


def check_no_pip_deps():
    forbidden = ["requirements.txt", "Pipfile", "pyproject.toml", "package.json"]
    found = [p for p in forbidden if os.path.exists(os.path.join(ROOT, p))]
    if found:
        _fail("forbidden dependency manifests present:")
        for p in found:
            print("   - " + p)
        return False
    _ok("no pip/npm dependency manifests present (stdlib + CDN only)")
    return True


def run_tests():
    tests_dir = os.path.join(ROOT, "tests")
    if not os.path.isdir(tests_dir):
        _fail("tests/ directory missing")
        return False
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
    )
    if proc.returncode != 0:
        _fail("test suite failed")
        return False
    _ok("test suite passed")
    return True


def main():
    checks = [
        check_required_dirs,
        check_required_files,
        check_architecture_sections,
        check_single_calc_file,
        check_no_pip_deps,
        check_proprietary_isolation,
        run_tests,
    ]
    ok = True
    for c in checks:
        if not c():
            ok = False
    print("")
    if ok:
        print("VALIDATE: PASS")
        sys.exit(0)
    else:
        print("VALIDATE: FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()
