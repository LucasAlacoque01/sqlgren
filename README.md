
# SQL DocGen

> Documentação automática de consultas SQL baseada em análise estrutural.

O **SQL DocGen** é uma ferramenta CLI que lê arquivos `.sql`, analisa sua estrutura usando `sqlglot` e gera **um único HTML** com documentação clara, organizada e legível para humanos.

Ele foi criado para resolver um problema comum em times de dados e backend:

> *"Temos muitas queries, mas ninguém sabe exatamente o que cada uma faz."*

---

## ✨ Principais recursos

* 📂 Leitura recursiva de arquivos `.sql`
* 🧠 Análise estrutural (tabelas, métricas, dimensões, joins)
* ✍️ Geração automática de **título e descrição em linguagem natural**
* 📊 Classificação de complexidade da query
* 🌐 Geração de **HTML único**, estático e portátil
* 🧩 Arquitetura modular e extensível

---

## 📸 Exemplo de saída

O HTML gerado inclui, para cada query:

* Título automático
* Descrição textual do que a query faz
* Tipo (Listagem / Agregação)
* Complexidade (Simples / Média / Pesada)
* Tabelas envolvidas
* Métricas e dimensões
* SQL completo formatado

---

## 🏗️ Arquitetura do projeto

```
SQL_DOCGEN_HTML_UNICO/
├── analyzer.py # Análise estrutural das consultas SQL
├── cli.py # Orquestração via linha de comando (CLI)
├── generator.py # Geração do HTML final da documentação
├── interpreter.py # Conversão técnica do SQL para linguagem natural
├── html_theme.py # Definição de layout e tema HTML
├── queries/ # Consultas SQL de entrada
│ └── *.sql
├── output/ # Arquivos gerados
│ └── *.html
└── README.md # Documentação do projeto
```

Cada módulo tem **responsabilidade única**, facilitando manutenção e evolução.

---

## 🚀 Instalação

### Requisitos

* Python 3.11.6
* pip

### Dependências

```bash
pip install sqlglot
```

---

## ▶️ Como usar

1. Coloque suas queries na pasta `queries/` (com ou sem subpastas)

2. Execute o CLI:

```bash
py cli.py queries
```

3. Abra o arquivo gerado:

```
output/consultas.html
```

---

## 🧠 Como funciona

1. **Analyzer**

   * Lê o SQL
   * Identifica tabelas, métricas, dimensões, joins e subqueries

2. **Interpreter**

   * Gera título e descrição em linguagem natural

3. **Renderer**

   * Monta um HTML único com todos os blocos documentados

---

## 📌 Casos de uso

* Documentação de queries legadas
* Repositórios de BI / Analytics
* Times de dados e backend
* Órgãos públicos (saúde, indicadores, relatórios)
* Onboarding de novos desenvolvedores

---

## 🛣️ Roadmap

* [ ] Índice lateral por pasta
* [ ] Busca instantânea no HTML
* [ ] Collapse / expand do SQL
* [ ] Detecção de domínio (ex: vacinação, financeiro)
* [ ] Suporte avançado a CTEs e UNION
* [ ] Exportação para PDF

---

## 🤝 Contribuindo

Contribuições são muito bem-vindas!

1. Faça um fork do projeto
2. Crie uma branch (`feature/minha-feature`)
3. Commit suas alterações
4. Abra um Pull Request

Sugestões, issues e melhorias de heurística são especialmente bem-vindas.

---

## 📄 Licença

MIT License.

---

## 👤 Autor

Projeto idealizado e desenvolvido por **Alacoque**.

Se este projeto te ajudou, considere deixar uma ⭐ no repositório.
