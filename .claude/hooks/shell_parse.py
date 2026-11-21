from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

CONTROL_CHARS = ";&|()"
REDIRECT = re.compile(r"^\d*(?:>>?|>\||&>>?)$")
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
GIT_OPTS_WITH_VALUE = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})
DELETE_FLAGS = frozenset({"-d", "--delete"})
WRITING_COMMANDS = frozenset({"tee", "cp", "mv", "rm", "truncate", "install", "ln"})
IN_PLACE_EDITORS = frozenset({"sed", "perl"})


def segments(command: str) -> list[list[str]]:
    """return(list): one token list per simple command; quoted text stays inside one token."""
    lexer = shlex.shlex(
        command.replace("\n", ";"), posix=True, punctuation_chars=CONTROL_CHARS + "<>"
    )
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    out: list[list[str]] = []
    current: list[str] = []
    for tok in tokens:
        if tok and set(tok) <= set(CONTROL_CHARS):
            if current:
                out.append(current)
            current = []
        else:
            current.append(tok)
    if current:
        out.append(current)
    return [seg for seg in (_drop_assignments(s) for s in out) if seg]


def _drop_assignments(seg: list[str]) -> list[str]:
    i = 0
    while i < len(seg) and ASSIGNMENT.match(seg[i]):
        i += 1
    return seg[i:]


def cd_target(where: Path, args: list[str]) -> Path:
    """return(Path): the directory after `cd args`; unresolvable targets keep `where`."""
    if not args:
        return Path.home()
    raw = os.path.expanduser(os.path.expandvars(args[0]))
    if args[0] == "-" or "$" in raw:
        return where
    return (where / raw).resolve()


def git_subcommand(seg: list[str]) -> tuple[str | None, list[str], str | None]:
    """return(tuple): (subcommand, its args, -C dir) for a `git ...` segment, else (None, [], None)."""
    if not seg or Path(seg[0]).name != "git":
        return None, [], None
    gitdir = None
    i = 1
    while i < len(seg):
        tok = seg[i]
        if tok in GIT_OPTS_WITH_VALUE:
            if tok == "-C" and i + 1 < len(seg):
                gitdir = seg[i + 1]
            i += 2
        elif tok.startswith("-"):
            i += 1
        else:
            return tok, seg[i + 1 :], gitdir
    return None, [], gitdir


def push_dir(command: str, cwd: Path) -> Path | None:
    """return(Path | None): the directory a push in `command` runs from, or None when it doesn't push."""
    where = cwd
    for seg in segments(command):
        if seg[0] == "cd":
            where = cd_target(where, seg[1:])
            continue
        if seg[:3] == ["gh", "pr", "create"]:
            return where
        sub, args, gitdir = git_subcommand(seg)
        deletes = DELETE_FLAGS.intersection(args) or any(a.startswith(":") for a in args)
        if sub != "push" or deletes:
            continue
        return (where / os.path.expanduser(gitdir)).resolve() if gitdir else where
    return None


def _is_in_place_flag(arg: str) -> bool:
    if arg.startswith("--"):
        return arg.split("=", 1)[0] == "--in-place"
    return arg.startswith("-") and "i" in arg[1:]


def _command_targets(seg: list[str]) -> list[str]:
    name = Path(seg[0]).name
    args = [a for a in seg[1:] if not a.startswith("-") and not REDIRECT.match(a)]
    if name in WRITING_COMMANDS:
        return args
    if name in IN_PLACE_EDITORS and any(_is_in_place_flag(a) for a in seg[1:]):
        return args
    if name == "dd":
        return [a.removeprefix("of=") for a in seg[1:] if a.startswith("of=")]
    return []


def write_targets(command: str, cwd: Path) -> list[Path]:
    """return(list): files `command` may write or delete via redirects or common file commands."""
    where = cwd
    found: list[Path] = []
    for seg in segments(command):
        if seg[0] == "cd":
            where = cd_target(where, seg[1:])
            continue
        raw = [seg[i + 1] for i, tok in enumerate(seg[:-1]) if REDIRECT.match(tok)]
        raw += _command_targets(seg)
        found += [(where / os.path.expanduser(r)).resolve() for r in raw if not r.isdigit()]
    return found
