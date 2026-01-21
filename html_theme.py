from datetime import datetime
from typing import Iterable, Dict, Any
import html


# =========================
# Utilidades básicas
# =========================

def esc(value: Any) -> str:
    """Escapa qualquer valor para HTML seguro."""
    return html.escape(str(value)) if value is not None else ""


def join_or_placeholder(items: Iterable[str], placeholder: str = "—") -> str:
    """Renderiza <li> ou placeholder quando vazio."""
    items = list(items or [])
    if not items:
        return f"<li>{placeholder}</li>"
    return "".join(f"<li>{esc(i)}</li>" for i in items)


# =========================
# Componentes HTML
# =========================

def render_badge(text: str) -> str:
    return f'<span class="badge">{esc(text)}</span>'


def render_list(title: str, items: Iterable[str]) -> str:
    return f"""
    <h4>{esc(title)}</h4>
    <ul>
        {join_or_placeholder(items)}
    </ul>
    """


def render_sql_block(sql: str) -> str:
    return f"""
    <h4>SQL</h4>
    <pre><code>{esc(sql)}</code></pre>
    """


def render_card(index: int, block: Dict[str, Any]) -> str:
    """
    Renderiza um card individual de consulta.
    Espera um view-model normalizado.
    """

    return f"""
    <section class="card" id="query-{index}">
        <h2>{index}. {esc(block['titulo'])}</h2>

        <p class="desc">{esc(block['descricao'])}</p>

        <div class="meta">
            {render_badge(block['tipo'])}
            {render_badge(block['complexidade'])}
        </div>

        <p class="file">
            <strong>Arquivo:</strong> {esc(block['arquivo'])}
        </p>

        {render_list("Tabelas", block['tabelas'])}
        {render_list("Métricas", block['metricas'])}
        {render_list("Dimensões", block['dimensoes'])}
        {render_sql_block(block['sql'])}
    </section>
    """


# =========================
# Página completa
# =========================

def render_page(title: str, blocks: Iterable[Dict[str, Any]]) -> str:
    blocks = list(blocks)

    cards_html = (
        "".join(render_card(i, b) for i, b in enumerate(blocks, 1))
        if blocks
        else "<p>Nenhuma query encontrada.</p>"
    )

    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8" />
<title>{esc(title)}</title>

<style>
:root {{
    --bg: #0f172a;
    --card: #020617;
    --text: #e5e7eb;
    --primary: #2563eb;
    --muted: #94a3b8;
}}

body {{
    background: var(--bg);
    color: var(--text);
    font-family: system-ui, -apple-system, sans-serif;
    margin: 0;
}}

.container {{
    max-width: 1200px;
    margin: auto;
    padding: 40px;
}}

.card {{
    background: var(--card);
    padding: 24px;
    border-radius: 12px;
    margin-bottom: 32px;
}}

.badge {{
    background: var(--primary);
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    margin-right: 6px;
}}

.meta {{
    margin: 8px 0 16px;
}}

.desc {{
    opacity: 0.85;
}}

.file {{
    font-size: 14px;
    color: var(--muted);
}}

pre {{
    background: #020617;
    padding: 16px;
    overflow-x: auto;
    border-radius: 8px;
}}

footer {{
    opacity: 0.6;
    margin-top: 48px;
    font-size: 14px;
}}
</style>
</head>

<body>
<div class="container">
    <h1>{esc(title)}</h1>
    <p>Documentação automática baseada em análise estrutural de consultas SQL.</p>

    {cards_html}

    <footer>
        Gerado em {generated_at}
    </footer>
</div>
</body>
</html>
"""
