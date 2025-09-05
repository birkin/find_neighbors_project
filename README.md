# find_neighbors_project

A small utility to find occurrences of two terms within N words of each other in a text.

## Run tests

Use Python's built-in unittest via `uv`:

```bash
uv run -m unittest -v
```

or

```bash
uv run -m unittest discover -s tests -p 'test_*.py' -v
```

## CLI usage

Example invocation of the script:

```bash
uv run find_neighbors.py \
  --filepath path/to/file.txt \
  --term1 cats \
  --term2 dogs \
  --nearness 3
```
