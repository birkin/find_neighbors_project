# /// script
# requires-python = "==3.12.*"
# dependencies = []
# ///

## Find two terms within N words of each other in a text file (case-insensitive)
import argparse
import re
import sys
from pathlib import Path

DEFAULT_NEARNESS: int = 10


def build_pattern(term1: str, term2: str, nearness: int) -> re.Pattern:
    # Escape terms to ensure literal matching in regex
    term1: str = re.escape(term1)
    term2: str = re.escape(term2)
    between: str = rf'(?:\W+\w+){{0,{nearness}}}?\W*'
    # Named groups allow us to determine which term appears first in the match
    pattern_str: str = (
        rf'(?:'
        rf'(?P<a>{term1})(?P<between1>{between})(?P<b>{term2})'
        rf'|'
        rf'(?P<b2>{term2})(?P<between2>{between})(?P<a2>{term1})'
        rf')'
    )
    compiled: re.Pattern = re.compile(pattern_str, re.IGNORECASE)
    return compiled


def find_neighbors_in_text(text: str, term1: str, term2: str, nearness: int) -> dict:
    """
    Find occurrences of two terms within N words of each other in the provided text.

    Returns a JSON-serializable dictionary with the following shape:
        {
            "count": int,
            "matches": [
                {"snippet": str},
                ...
            ]
        }
    """
    nearness = max(int(nearness), 0)
    pattern: re.Pattern = build_pattern(term1, term2, nearness)

    def extract_context(src: str, first_start: int, second_end: int, pre_words: int = 10, post_words: int = 10) -> tuple[str, str]:
        tokens: list[re.Match] = list(re.finditer(r'\w+', src))

        # Pre-context: last `pre_words` tokens ending before or at first_start
        pre_last_idx: int = -1
        for i, tm in enumerate(tokens):
            if tm.end() <= first_start:
                pre_last_idx = i
            else:
                break
        pre_tokens: list[re.Match] = tokens[max(0, pre_last_idx - pre_words + 1): pre_last_idx + 1] if pre_last_idx >= 0 else []
        pre: str = ' '.join(t.group(0) for t in pre_tokens)

        # Post-context: first `post_words` tokens starting at or after second_end
        post_start_idx: int | None = None
        for i, tm in enumerate(tokens):
            if tm.start() >= second_end:
                post_start_idx = i
                break
        post_tokens: list[re.Match] = tokens[post_start_idx: post_start_idx + post_words] if post_start_idx is not None else []
        post: str = ' '.join(t.group(0) for t in post_tokens)

        return pre, post

    results: list[dict[str, str]] = []
    for m in pattern.finditer(text):
        # Determine which ordering matched and get the span from the first term to the second term
        if m.group('a') is not None:
            first_start: int = m.start('a')
            second_end: int = m.end('b')
        else:
            first_start = m.start('b2')
            second_end = m.end('a2')

        core: str = text[first_start:second_end].replace('\n', ' ')
        pre, post = extract_context(text, first_start, second_end, 10, 10)
        snippet: str = f"{pre} {core} {post}".strip()
        results.append({"snippet": snippet})

    return {"count": len(results), "matches": results}


def parse_args() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description='Find occurrences of two terms within N words of each other in a file.'
    )
    parser.add_argument(
        '--filepath',
        required=True,
        help='Path to the text file to search',
    )
    parser.add_argument(
        '--nearness',
        type=int,
        default=DEFAULT_NEARNESS,
        help=f'Maximum number of words allowed between the two terms (default: {DEFAULT_NEARNESS})',
    )
    parser.add_argument(
        '--term1',
        required=True,
        help='First term to search for',
    )
    parser.add_argument(
        '--term2',
        required=True,
        help='Second term to search for',
    )
    args: argparse.Namespace = parser.parse_args()
    return args


def main() -> int:
    args: argparse.Namespace = parse_args()

    path: Path = Path(args.filepath)
    if not path.exists() or not path.is_file():
        print(f'Error: file not found: {path}', file=sys.stderr)
        return 1

    try:
        text: str = path.read_text(encoding='utf-8')
    except Exception as exc:
        print(f'Error reading file {path}: {exc}', file=sys.stderr)
        return 1

    # Delegate the search to the library function
    result: dict = find_neighbors_in_text(
        text=text,
        term1=args.term1,
        term2=args.term2,
        nearness=args.nearness,
    )

    print(f"found {result['count']} match(es)")
    for item in result.get('matches', []):
        snippet = item.get('snippet', '')
        print()
        print(f'- match="{snippet}"')

    return 0


if __name__ == '__main__':
    sys.exit(main())
