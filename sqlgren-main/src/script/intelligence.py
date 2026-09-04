"""Compat: src.script.intelligence → src.core.intelligence + translator."""

from src.core.intelligence import *  # noqa: F403
from src.core.intelligence import build_impact, find_twins
from src.core.translator import pretty_sql, transpile_sql

__all__ = ["build_impact", "find_twins", "pretty_sql", "transpile_sql"]
