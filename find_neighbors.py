#!/usr/bin/env python3
## finds neighbors of two terms within N words and prints highlighted snippets

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import TypedDict

## constants
DEFAULT_NEARNESS = 10
DEFAULT_PRE_WORDS = 10
DEFAULT_POST_WORDS = 10


## data types
class MatchDict(TypedDict):
    snippet: str


class ResultDict(TypedDict):
    count: int
    matches: list[MatchDict]


## builds compiled regex for order-agnostic, substring-allowed match across newlines
def build_pattern(term1: str, term2: str, nearness: int) -> re.Pattern[str]:
    t1 = re.escape(term1)
    t2 = re.escape(term2)

    # between = up to N words in-between, counting by \S+ tokens
    between = rf'\S*(?:\s+\S+){{0,{nearness}}}?\s*\S*'

    pat = (
        rf'(?:'
        rf'(?P<a>{t1})(?P<between1>{between})(?P<b>{t2})'
        rf'|'
        rf'(?P<b2>{t2})(?P<between2>{between})(?P<a2>{t1})'
        rf')'
    )
    return re.compile(pat, re.IGNORECASE | re.DOTALL)


## slices context in tokens around a [first_start, second_end) span
def _slice_context(
    text: str,
    token_matches: list[re.Match[str]],
    first_start: int,
    second_end: int,
    pre_words: int,
    post_words: int,
) -> tuple[str, str, str]:
    # find token index containing first_start
    first_token_idx = 0
    for i, tm in enumerate(token_matches):
        if tm.start() <= first_start < tm.end():
            first_token_idx = i
            break

    pre_tokens = token_matches[max(0, first_token_idx - pre_words) : first_token_idx]
    pre = ' '.join(t.group(0) for t in pre_tokens)

    # find token index starting at/after second_end
    post_start_idx: int | None = None
    for i, tm in enumerate(token_matches):
        if tm.start() >= second_end:
            post_start_idx = i
            break
    post_tokens = token_matches[post_start_idx : post_start_idx + post_words] if post_start_idx is not None else []
    post = ' '.join(t.group(0) for t in post_tokens)

    core = text[first_start:second_end]
    return pre, core, post


## core search routine: returns snippets with exactly the two matched substrings highlighted
def find_neighbors_in_text(
    text: str,
    term1: str,
    term2: str,
    nearness: int = DEFAULT_NEARNESS,
    pre_words: int = DEFAULT_PRE_WORDS,
    post_words: int = DEFAULT_POST_WORDS,
) -> ResultDict:
    pat = build_pattern(term1, term2, nearness)
    results: list[MatchDict] = []

    token_matches = list(re.finditer(r'\S+', text, re.DOTALL))

    for m in pat.finditer(text):
        if m.group('a') is not None:
            first_start, second_end = m.start('a'), m.end('b')
            span1 = (m.start('a'), m.end('a'))
            span2 = (m.start('b'), m.end('b'))
        else:
            first_start, second_end = m.start('b2'), m.end('a2')
            span1 = (m.start('b2'), m.end('b2'))
            span2 = (m.start('a2'), m.end('a2'))

        # order spans by appearance
        s1, s2 = (span1, span2) if span1[0] <= span2[0] else (span2, span1)

        pre, core_src, post = _slice_context(text, token_matches, first_start, second_end, pre_words, post_words)

        # core-relative indices
        r1 = (s1[0] - first_start, s1[1] - first_start)
        r2 = (s2[0] - first_start, s2[1] - first_start)

        # insert markers; do earlier span first, then adjust later span by +6
        c = core_src
        c = c[: r1[0]] + '|||' + c[r1[0] : r1[1]] + '|||' + c[r1[1] :]
        shift = 6  # len('|||') * 2
        r2 = (r2[0] + shift, r2[1] + shift)
        c = c[: r2[0]] + '|||' + c[r2[0] : r2[1]] + '|||' + c[r2[1] :]

        # normalize newlines in the core only (avoid backslash in f-string expr)
        clean_core = c.replace('\n', ' ')
        snippet = f'{pre} {clean_core} {post}'.strip()

        results.append({'snippet': snippet})

    return {'count': len(results), 'matches': results}


## io helpers
def _read_text_from_path_or_stdin(filepath: str | None) -> str:
    if not filepath or filepath == '-':
        return sys.stdin.read()
    p = Path(filepath)
    return p.read_text(encoding='utf-8')


## cli
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='find_neighbors',
        description='find occurrences of two terms within N words, highlight them, and print context',
    )
    parser.add_argument(
        '--filepath',
        help='path to input file (use "-" for stdin)',
        required=False,
        default='-',
    )
    parser.add_argument(
        '--term1',
        help='first term to search',
        required=True,
    )
    parser.add_argument(
        '--term2',
        help='second term to search',
        required=True,
    )
    parser.add_argument(
        '--nearness',
        type=int,
        default=DEFAULT_NEARNESS,
        help=f'max words between terms (default: {DEFAULT_NEARNESS})',
    )
    parser.add_argument(
        '--pre-words',
        type=int,
        default=DEFAULT_PRE_WORDS,
        help=f'words of context before first term (default: {DEFAULT_PRE_WORDS})',
    )
    parser.add_argument(
        '--post-words',
        type=int,
        default=DEFAULT_POST_WORDS,
        help=f'words of context after second term (default: {DEFAULT_POST_WORDS})',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='emit json instead of pretty text',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    text = _read_text_from_path_or_stdin(args.filepath)

    res = find_neighbors_in_text(
        text=text,
        term1=args.term1,
        term2=args.term2,
        nearness=args.nearness,
        pre_words=args.pre_words,
        post_words=args.post_words,
    )

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    print(f'count: {res["count"]}')
    for i, m in enumerate(res['matches'], start=1):
        print(f'[{i}] {m["snippet"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
