// ===============================
// DATA (injetado pelo Python)
// app.js

const queries = window.QUERIES || [];

if (!Array.isArray(queries)) {
  console.error("QUERIES não foi carregado corretamente");
}


// ===============================
// CONFIGURAÇÃO PADRÃO
// ===============================
const defaultConfig = {
  page_title: 'SQL DocGen',
  subtitle: 'Documentação automática',
  primary_color: '#3b82f6',
  secondary_color: '#8b5cf6',
  accent_color: '#10b981',
  bg_color: '#0a0a0f',
  text_color: '#f1f5f9',
  font_family: 'Space Grotesk',
  font_size: 16
};

let config = { ...defaultConfig };
let currentFilter = 'all';
let searchTerm = '';

// ===============================
// SQL SYNTAX HIGHLIGHT
// ===============================
function highlightSQL(sql) {
  const keywords = [
    'SELECT','FROM','WHERE','AND','OR','JOIN','INNER','LEFT','RIGHT','OUTER',
    'ON','GROUP','BY','ORDER','HAVING','LIMIT','OFFSET','AS','DISTINCT',
    'COUNT','SUM','AVG','MAX','MIN','CASE','WHEN','THEN','ELSE','END',
    'INSERT','INTO','VALUES','UPDATE','SET','DELETE','CREATE','ALTER',
    'DROP','TABLE','INDEX','VIEW','WITH','UNION','ALL','EXISTS','IN',
    'NOT','NULL','IS','BETWEEN','LIKE','OVER','PARTITION','INTERVAL',
    'DATE','CURRENT_DATE','CURRENT_TIMESTAMP','TRUE','FALSE','ASC','DESC',
    'ROUND','LAG','UUID','DATEDIFF','DATE_SUB','DAY','YEAR'
  ];

  let escaped = sql
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  escaped = escaped.replace(/(--.*$)/gm, '<span class="sql-comment">$1</span>');
  escaped = escaped.replace(/('(?:[^'\\]|\\.)*')/g, '<span class="sql-string">$1</span>');
  escaped = escaped.replace(/\b(\d+\.?\d*)\b/g, '<span class="sql-number">$1</span>');

  keywords.forEach(kw => {
    const regex = new RegExp(`\\b(${kw})\\b`, 'gi');
    escaped = escaped.replace(regex, '<span class="sql-keyword">$1</span>');
  });

  escaped = escaped.replace(/(:\w+)/g, '<span class="sql-column">$1</span>');

  return escaped;
}

// ===============================
// COMPLEXIDADE
// ===============================
function getComplexityClass(complexity) {
  const c = complexity.toLowerCase();
  if (c === 'baixa' || c === 'low') return 'badge-complexity-baixa';
  if (c === 'média' || c === 'media' || c === 'medium') return 'badge-complexity-media';
  return 'badge-complexity-alta';
}

// ===============================
// RENDER CARD
// ===============================
function renderCard(query, index) {
  const sqlLines = query.sql.trim().split('\n');

  const highlightedLines = sqlLines.map((line, i) =>
    `<tr>
      <td class="line-number">${i + 1}</td>
      <td>${highlightSQL(line)}</td>
    </tr>`
  ).join('');

  const tablesHtml = query.tabelas.map(t =>
    `<span class="table-pill">${t}</span>`
  ).join('');

  const metricsHtml = query.metricas.length
    ? query.metricas.map(m => `<div class="metric-card">${m}</div>`).join('')
    : '—';

  const dimensionsHtml = query.dimensoes.length
    ? query.dimensoes.map(d => `<div class="dimension-card">${d}</div>`).join('')
    : '—';

  return `
    <article id="query-${index}" class="gradient-border card-glow fade-in">
      <div class="p-6">

        <h3>${query.titulo}</h3>
        <p>${query.descricao}</p>

        <div>${tablesHtml}</div>
        <div>${metricsHtml}</div>
        <div>${dimensionsHtml}</div>

        <div class="sql-block">
          <table>
            <tbody>${highlightedLines}</tbody>
          </table>
        </div>

      </div>
    </article>
  `;
}

// ===============================
// SIDEBAR NAV
// ===============================
function renderNav(queries) {
  return queries.map((q, i) => `
    <a href="#query-${i + 1}" class="sidebar-item">
      <span>${i + 1}</span>
      <span>${q.titulo}</span>
    </a>
  `).join('');
}

// ===============================
// FILTRO
// ===============================
function filterQueries() {
  let filtered = sampleQueries;

  if (currentFilter !== 'all') {
    filtered = filtered.filter(q =>
      q.tipo.toUpperCase() === currentFilter.toUpperCase()
    );
  }

  if (searchTerm) {
    const term = searchTerm.toLowerCase();
    filtered = filtered.filter(q =>
      q.titulo.toLowerCase().includes(term) ||
      q.descricao.toLowerCase().includes(term)
    );
  }

  return filtered;
}

// ===============================
// RENDER GERAL
// ===============================
function renderAll() {
  const filtered = filterQueries();

  document.getElementById('cards-container').innerHTML =
    filtered.map((q, i) => renderCard(q, i + 1)).join('');

  document.getElementById('query-nav').innerHTML = renderNav(filtered);
  document.getElementById('total-queries').textContent = filtered.length;

  const allTables = [...new Set(filtered.flatMap(q => q.tabelas))];
  document.getElementById('total-tables').textContent = allTables.length;
}

// ===============================
// COPY SQL
// ===============================
function copySQL(index) {
  const query = filterQueries()[index - 1];
  if (query) {
    navigator.clipboard.writeText(query.sql);
  }
}

// ===============================
// EVENTOS
// ===============================
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    currentFilter = btn.id.replace('filter-', '');
    renderAll();
  });
});

document.getElementById('search-input')
  .addEventListener('input', e => {
    searchTerm = e.target.value;
    renderAll();
  });

// ===============================
// INIT
// ===============================
renderAll();

const now = new Date();
document.getElementById('generated-at').textContent =
  `Gerado em ${now.toLocaleDateString('pt-BR')} ${now.toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit'
  })}`;
