"""Núcleo de análise estrutural do Acervo (zero execução)."""

from .analyzer import analyze_sql
from .catalog import build_catalog
from .collector import collect_sql_files, read_sql_file
from .generator import normalize_block
from .intelligence import find_twins, build_impact, compute_health
from .interpreter import interpretar
from .lineage import build_lineage
from .translator import pretty_sql, transpile_sql

__all__ = [
    "analyze_sql",
    "build_catalog",
    "build_impact",
    "build_lineage",
    "collect_sql_files",
    "compute_health",
    "find_twins",
    "interpretar",
    "normalize_block",
    "pretty_sql",
    "read_sql_file",
    "transpile_sql",
]
