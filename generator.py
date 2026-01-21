from typing import Dict, Any
from html_theme import render_query_block


def generate_block(name: str, sql: str, info: Dict[str, Any]) -> str:
    """
    Gera um bloco HTML documentado para uma query SQL.

    Responsabilidades desta função:
    - Validar dados de entrada
    - Normalizar campos esperados pelo tema HTML
    - Garantir segurança e consistência da apresentação
    - Isolar a camada de renderização do restante do sistema
    """

    if not name:
        raise ValueError("Nome do bloco não pode ser vazio")

    if not sql or not sql.strip():
        raise ValueError(f"SQL vazio no bloco '{name}'")

    if not isinstance(info, dict):
        raise TypeError("O parâmetro 'info' deve ser um dicionário")

    # 1️⃣ Normalização defensiva (view-model)
    block_info = {
        "titulo": info.get("titulo", name),
        "descricao": info.get("descricao", ""),
        "tipo": info.get("tipo", "Desconhecido"),
        "complexidade": info.get("complexidade", "N/A"),
        "tabelas": info.get("tabelas", []),
        "metricas": info.get("metricas", []),
        "dimensoes": info.get("dimensoes", []),
    }

    # 2️⃣ Higienização básica do SQL (apresentação)
    sql_clean = sql.strip()

    # 3️⃣ Geração do HTML isolada
    return render_query_block(
        name=block_info["titulo"],
        sql=sql_clean,
        info=block_info,
    )
