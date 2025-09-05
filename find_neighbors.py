# /// script
# requires-python = "==3.12.*"
# dependencies = []
# ///

"""
Finds occurrences of two terms within N words of each other in a text file (case-insensitive).
The returned snippets highlight the first and second term with ||| markers.

Returns a JSON-serializable dictionary with the following shape:
    {
        "count": int,
        "matches": [
            {"snippet": str},
            ...
        ]
    }
"""

import argparse
import re
import sys
from pathlib import Path

DEFAULT_NEARNESS: int = 10


def build_pattern(term1: str, term2: str, nearness: int) -> re.Pattern:
    # Escape terms to ensure literal matching in regex
    term1: str = re.escape(term1)
    term2: str = re.escape(term2)
    # Count nearness by whitespace-separated tokens (\S+) rather than \w words.
    # Allow the term to appear as a substring within a token by:
    # - consuming the remainder of the current token after term1 (\S*)
    # - then up to N whitespace+token groups
    # - then optional whitespace and the beginning of the next token before term2 (\S*)
    between: str = rf'\S*(?:\s+\S+){{0,{nearness}}}?\s*\S*'
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

    def extract_context(
        src: str, first_start: int, second_end: int, pre_words: int = 10, post_words: int = 10
    ) -> tuple[str, str, str]:
        tokens: list[re.Match] = list(re.finditer(r'\w+', src))

        # Pre-context: last `pre_words` tokens ending before or at first_start
        pre_last_idx: int = -1
        for i, tm in enumerate(tokens):
            if tm.end() <= first_start:
                pre_last_idx = i
            else:
                break
        pre_tokens: list[re.Match] = (
            tokens[max(0, pre_last_idx - pre_words + 1) : pre_last_idx + 1] if pre_last_idx >= 0 else []
        )
        pre: str = ' '.join(t.group(0) for t in pre_tokens)

        # Post-context: first `post_words` tokens starting at or after second_end
        post_start_idx: int | None = None
        for i, tm in enumerate(tokens):
            if tm.start() >= second_end:
                post_start_idx = i
                break
        post_tokens: list[re.Match] = (
            tokens[post_start_idx : post_start_idx + post_words] if post_start_idx is not None else []
        )
        post: str = ' '.join(t.group(0) for t in post_tokens)

        # Core slice between the first and second matched spans (raw, without highlighting)
        core_src: str = src[first_start:second_end]

        return pre, core_src, post

    def massage_highlight(
        core: str, first_abs_span: tuple[int, int], second_abs_span: tuple[int, int], core_abs_start: int
    ) -> str:
        """Add ||| markers around the first and second matched terms inside the provided core.
        Expands the first term to include trailing word characters to capture full tokens (e.g., mysqldump).
        `core_abs_start` is the absolute position in the full text where `core` begins.
        """
        # Expand only the FIRST matched span to include trailing word chars (alnum/underscore)
        fs0, fs1 = first_abs_span
        while fs1 < len(text) and (text[fs1].isalnum() or text[fs1] == '_'):
            fs1 += 1
        first_span_expanded = (fs0, fs1)

        # Compute relative indices inside the core
        rel1_start = first_span_expanded[0] - core_abs_start
        rel1_end = first_span_expanded[1] - core_abs_start
        rel2_start = second_abs_span[0] - core_abs_start
        rel2_end = second_abs_span[1] - core_abs_start

        # Clamp to valid bounds
        rel1_start = max(rel1_start, 0)
        rel1_end = max(rel1_end, 0)
        rel2_start = max(rel2_start, 0)
        rel2_end = max(rel2_end, 0)

        # Insert markers in textual order: first term then second term
        highlighted = (
            core[:rel1_start]
            + '|||'
            + core[rel1_start:rel1_end]
            + '|||'
            + core[rel1_end:rel2_start]
            + '|||'
            + core[rel2_start:rel2_end]
            + '|||'
            + core[rel2_end:]
        )
        return highlighted

    results: list[dict[str, str]] = []
    for m in pattern.finditer(text):
        # Determine which ordering matched and get the span from the first term to the second term
        if m.group('a') is not None:
            first_start: int = m.start('a')
            second_end: int = m.end('b')
            span1 = (m.start('a'), m.end('a'))
            span2 = (m.start('b'), m.end('b'))
        else:
            first_start = m.start('b2')
            second_end = m.end('a2')
            span1 = (m.start('b2'), m.end('b2'))
            span2 = (m.start('a2'), m.end('a2'))

        # Order spans by appearance in the text to determine first/second matched words
        first_span, second_span = (span1, span2) if span1[0] <= span2[0] else (span2, span1)

        # Build the raw core and pre/post context first, then pass through a massaging function
        pre, core_src, post = extract_context(text, first_start, second_end, 10, 10)

        highlighted_core = massage_highlight(core_src, first_span, second_span, first_start)
        core: str = highlighted_core.replace('\n', ' ')
        snippet: str = f'{pre} {core} {post}'.strip()
        results.append({'snippet': snippet})

    return {'count': len(results), 'matches': results}


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

    print(f'found {result["count"]} match(es)')
    for item in result.get('matches', []):
        snippet = item.get('snippet', '')
        print()
        print(f'- match="{snippet}"')

    return 0


if __name__ == '__main__':
    sys.exit(main())
