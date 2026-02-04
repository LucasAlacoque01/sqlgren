import json
import html
from pathlib import Path
from typing import Iterable, Dict, Any

# Utilidades básicas
def esc(value: Any) -> str:
    """
    Escapa qualquer valor para HTML seguro (previne XSS).
    NÃO usar para JSON que será injetado em <script>.
    """
    return html.escape(str(value)) if value is not None else ""

def load_template(template_name: str) -> str:
    """
    Carrega um template HTML da pasta templates/.
    Ex: load_template("front.html")
    """
    base_dir = Path(__file__).resolve().parent

    #  templates 
    templates_dir = base_dir / "templates"
    template_path = templates_dir / template_name

    if not template_path.exists():
        raise FileNotFoundError(
            f"Template não encontrado: {template_path}"
        )

    return template_path.read_text(encoding="utf-8")


# Renderização da página
def render_page(
    title: str,
    blocks: Iterable[Dict[str, Any]],
    template_name: str = "front.html"
) -> str:
    """
    Renderiza a página HTML substituindo:
    - {{title}} → título escapado
    - `{{ data }}`  → JSON puro com os blocks
    """
    template = load_template(template_name)

    blocks_json = json.dumps(list(blocks), ensure_ascii=False)

    return (
        template
        .replace("{{title}}", esc(title))
        .replace("`{{data}}`", blocks_json)
    )