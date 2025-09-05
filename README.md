# find_neighbors_project

A small utility to find occurrences of two terms within N words of each other in a text.

## Run tests

Use Python's built-in unittest via `uv`:

```bash
uv run -m unittest discover -s tests -v
```

- `-m` stands for module but there's no double-dash equivalent
- `-s` or `--start-directory`
- `-v` or `--verbose`


## CLI usage

Example invocation of the script:

```bash
uv run find_neighbors.py \
  --filepath path/to/file.txt \
  --term1 cats \
  --term2 dogs \
  --nearness 3
```
