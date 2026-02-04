
from typing import Dict, List


# Utilidades linguísticas

def lista_humana(itens: List[str]) -> str:
    """
    Converte ['A', 'B', 'C'] em:
    - 'A'
    - 'A e B'
    - 'A, B e C'
    """
    itens = list(itens or [])
    if not itens:
        return ""

    if len(itens) == 1:
        return itens[0]

    return ", ".join(itens[:-1]) + f" e {itens[-1]}"


# Geração semântica

def gerar_titulo(info: Dict) -> str:
    metricas = info.get("metricas", [])
    dimensoes = info.get("dimensoes", [])

    if metricas and dimensoes:
        return f"{lista_humana(metricas)} por {lista_humana(dimensoes)}"

    if metricas:
        return f"{lista_humana(metricas)} dos registros"

    if dimensoes:
        return f"Distribuição por {lista_humana(dimensoes)}"

    return "Listagem geral de registros"


def gerar_descricao(info: Dict) -> str:
    tipo = info.get("tipo", "Consulta")
    metricas = info.get("metricas", [])
    dimensoes = info.get("dimensoes", [])
    tabelas = info.get("tabelas", [])

    frases = [f"{tipo} de dados"]

    if metricas:
        frases.append(f"com cálculo de {lista_humana(metricas)}")

    if dimensoes:
        frases.append(f"agrupada por {lista_humana(dimensoes)}")

    if tabelas:
        frases.append(f"utilizando as tabelas {lista_humana(tabelas)}")

    return ". ".join(frases) + "."



# Interface pública

def interpretar(info: Dict) -> Dict:
    """
    Enriquece a análise estrutural com interpretação semântica.
    """
    return {
        **info,
        "titulo": gerar_titulo(info),
        "descricao": gerar_descricao(info),
    }