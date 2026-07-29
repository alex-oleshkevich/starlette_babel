ruff := "ruff@0.15.5"

default:
    @just --list

test *args:
    uv run pytest {{ args }}

testc *args:
    uv run pytest --cov --cov-report term-missing {{ args }}

lint *args:
    uv run prek run --all-files {{ args }}
