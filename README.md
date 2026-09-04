# SQL DocGen

> **Documentação automática, confiável e legível de consultas SQL — no nível de ferramentas enterprise.**

O **SQL DocGen** é uma ferramenta de linha de comando (CLI) que analisa **estruturalmente** arquivos SQL — **sem executar nenhuma query** — e gera **um único artefato HTML**, estático e portátil, contendo documentação clara, organizada e inteligível para humanos.

Este projeto resolve um problema real e recorrente em times de dados, backend e BI:

> *Consultas SQL críticas existem, funcionam e produzem resultados… mas ninguém sabe exatamente o que fazem, por que existem ou quão complexas são.*

O SQL DocGen transforma SQL em **conhecimento documentado**, auditável e compartilhável.

---

## 🎯 Por que o SQL DocGen existe?

Ferramentas tradicionais de dados normalmente focam em:

* execução
* performance
* resultados

O **SQL DocGen** foca em algo diferente — e frequentemente negligenciado:

👉 **compreensão estrutural e semântica do SQL**.

Ele foi projetado para cenários onde:

* há centenas ou milhares de queries legadas
* múltiplas pessoas trabalham no mesmo repositório
* onboarding técnico é lento e custoso
* auditoria, rastreabilidade e governança são críticos
* o SQL é um ativo de negócio, não apenas código

---

## ✨ Principais recursos

* 📂 Leitura recursiva de arquivos `.sql`
* 🧠 Análise estrutural baseada em **AST** (não regex)
* 🧩 Detecção automática de:

  * tabelas utilizadas
  * métricas (funções de agregação)
  * dimensões (`GROUP BY`)
  * quantidade de `JOINs`
  * subqueries
* ✍️ Geração automática de **títulos e descrições em linguagem natural**
* 📊 Classificação objetiva de complexidade estrutural
* 🌐 Geração de **HTML único**, estático e portátil
* 🔐 **Não executa SQL** (seguro para ambientes sensíveis)
* 🧱 Arquitetura modular, previsível e extensível

---

## 🖼️ Resultado gerado

Para cada query documentada, o HTML final apresenta:

* Título gerado automaticamente
* Descrição semântica do que a query faz
* Tipo da consulta (Listagem ou Agregação)
* Nível de complexidade (Simples / Média / Pesada)
* Tabelas envolvidas
* Métricas detectadas
* Dimensões de agrupamento
* SQL completo preservado

Tudo consolidado em **um único arquivo HTML**, fácil de:

* compartilhar
* versionar
* arquivar
* anexar a auditorias técnicas

Nenhum servidor. Nenhuma dependência frontend. Apenas HTML.

---

## 🏗️ Arquitetura do projeto

O SQL DocGen foi desenhado seguindo princípios claros de **responsabilidade única**, **separação de camadas** e **previsibilidade de comportamento**.

```
SQL_DOCGEN/
├── analyzer.py      # Análise estrutural do SQL (AST)
├── interpreter.py   # Interpretação semântica (linguagem natural)
├── generator.py     # Normalização e view-model dos blocos
├── html_theme.py    # Renderização e tema HTML
├── cli.py           # Interface de linha de comando (CLI)
├── assets/          # CSS e JS do HTML gerado
├── templates/       # Templates HTML
├── queries/         # Consultas SQL de entrada
│   └── **/*.sql
├── output/          # Artefatos gerados
│   └── consultas.html
└── README.md
```

### Visão conceitual do fluxo

1. **Analyzer**

   * Realiza parsing seguro do SQL
   * Caminha pela AST completa
   * Extrai a estrutura real da consulta

2. **Interpreter**

   * Converte estrutura em significado
   * Gera títulos e descrições determinísticas
   * Sem heurísticas frágeis ou IA generativa

3. **Generator**

   * Normaliza e valida dados para apresentação
   * Atua como view-model defensivo

4. **HTML Theme**

   * Renderiza HTML estático
   * Injeta dados via JSON de forma segura

5. **CLI**

   * Orquestra todo o fluxo
   * Isola falhas por arquivo
   * Gera relatórios confiáveis

---

## 🔬 Como funciona internamente

### 🔍 Análise estrutural

* Parsing seguro via `sqlglot`
* Construção de AST (Abstract Syntax Tree)
* Caminhamento completo da árvore
* Identificação de elementos semânticos reais (tabelas, métricas, dimensões, joins)

### 🧠 Interpretação semântica

* Geração determinística de títulos
* Construção de descrições legíveis para humanos
* Totalmente previsível, auditável e reprodutível

### 🌐 Renderização

* HTML estático e portátil
* Sem execução de código SQL
* Sem dependência de backend ou banco de dados

---

## 🚀 Instalação

### Requisitos

* Python **3.11+**
* `pip`

### Dependência principal

```bash
pip install sqlglot
```

---

## ▶️ Como usar

1. Organize suas queries em uma pasta:

```
queries/
├── indicadores/
│   ├── vacinacao.sql
│   └── gestantes.sql
├── relatorios/
│   └── producao.sql
```

2. Execute o SQL DocGen:

```bash
python cli.py queries
```

3. Abra o arquivo gerado:

```
output/consultas.html
```

---

## 📌 Casos de uso reais

* Documentação de SQL legado
* Repositórios de BI e Analytics
* Times de backend e dados
* Auditorias técnicas
* Órgãos públicos e indicadores oficiais
* Onboarding de novos desenvolvedores

---

## 🛣️ Roadmap

* [ ] Índice lateral por pastas
* [ ] Busca instantânea no HTML (client-side)
* [ ] Collapse / expand do SQL
* [ ] Suporte avançado a CTEs e `UNION`
* [ ] Detecção automática de domínio semântico
* [ ] Exportação para PDF

---

## 🤝 Contribuindo

Contribuições são bem-vindas e incentivadas.

1. Faça um fork do projeto
2. Crie uma branch (`feature/sua-feature`)
3. Commit com mensagens claras
4. Abra um Pull Request

Discussões arquiteturais e melhorias semânticas são especialmente bem-vindas.

---

## 📄 Licença

MIT License.

---

## 👤 Autor

Projeto idealizado e desenvolvido por **Alacoque**.

Se este projeto te ajudou ou te impressionou tecnicamente, considere deixar uma ⭐ no repositório.
