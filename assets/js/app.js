
    
// Sample data - this would be injected by Python
     //let filtered = queries;
     
     //const sampleQuconsteries = JSON.parse(sampleQueriesJSON);
     console.log(sampleQueries)
// Default configuration
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

// Syntax highlighting for SQL
function highlightSQL(sql) {
  const keywords = ['SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'ON', 'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET', 'AS', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TABLE', 'INDEX', 'VIEW', 'WITH', 'UNION', 'ALL', 'EXISTS', 'IN', 'NOT', 'NULL', 'IS', 'BETWEEN', 'LIKE', 'OVER', 'PARTITION', 'INTERVAL', 'DATE', 'CURRENT_DATE', 'CURRENT_TIMESTAMP', 'TRUE', 'FALSE', 'ASC', 'DESC', 'ROUND', 'LAG', 'UUID', 'DATEDIFF', 'DATE_SUB', 'DAY', 'YEAR'];
  
  let escaped = sql.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  
  // Comments
  escaped = escaped.replace(/(--.*$)/gm, '<span class="sql-comment">$1</span>');
  
  // Strings
  escaped = escaped.replace(/('(?:[^'\\]|\\.)*')/g, '<span class="sql-string">$1</span>');
  
  // Numbers
  escaped = escaped.replace(/\b(\d+\.?\d*)\b/g, '<span class="sql-number">$1</span>');
  
  // Keywords
  keywords.forEach(kw => {
    const regex = new RegExp(`\\b(${kw})\\b`, 'gi');
    escaped = escaped.replace(regex, '<span class="sql-keyword">$1</span>');
  });
  
  // Parameters
  escaped = escaped.replace(/(:\w+)/g, '<span class="sql-column">$1</span>');
  
  return escaped;
}

function getComplexityClass(complexity) {
  const c = complexity.toLowerCase();
  if (c === 'baixa' || c === 'low') return 'badge-complexity-baixa';
  if (c === 'média' || c === 'media' || c === 'medium') return 'badge-complexity-media';
  return 'badge-complexity-alta';
}

function renderCard(query, index) {
  const sqlLines = query.sql.trim().split('\n');
  const highlightedLines = sqlLines.map((line, i) => 
    `<tr><td class="line-number pr-4 py-0.5">${i + 1}</td><td class="pl-4 py-0.5">${highlightSQL(line)}</td></tr>`
  ).join('');

  const tablesHtml = query.tabelas.map(t => 
    `<span class="table-pill px-3 py-1.5 rounded-lg text-xs font-mono" style="color: var(--accent-amber);">${t}</span>`
  ).join('');

  const metricsHtml = query.metricas.length ? query.metricas.map(m => 
    `<div class="metric-card px-3 py-2 rounded-lg">
      <span class="text-xs font-mono" style="color: var(--accent-blue);">${m}</span>
    </div>`
  ).join('') : '<span class="text-sm" style="color: var(--text-muted);">—</span>';

  const dimensionsHtml = query.dimensoes.length ? query.dimensoes.map(d => 
    `<div class="dimension-card px-3 py-2 rounded-lg">
      <span class="text-xs font-mono" style="color: var(--accent-emerald);">${d}</span>
    </div>`
  ).join('') : '<span class="text-sm" style="color: var(--text-muted);">—</span>';

  return `
    <article id="query-${index}" class="gradient-border card-glow fade-in stagger-${(index % 4) + 1}" style="opacity: 0;">
      <div class="p-6">
        <!-- Header -->
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-xl flex items-center justify-center font-display font-bold text-lg" 
                 style="background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple)); color: white;">
              ${index}
            </div>
            <div>
              <h3 class="font-display font-semibold text-xl" style="color: var(--text-primary);">${query.titulo}</h3>
              <p class="text-sm font-mono" style="color: var(--text-muted);">${query.arquivo}</p>
            </div>
          </div>
          <div class="flex gap-2">
            <span class="badge-type px-3 py-1.5 rounded-full text-xs font-semibold">${query.tipo}</span>
            <span class="${getComplexityClass(query.complexidade)} px-3 py-1.5 rounded-full text-xs font-semibold">${query.complexidade}</span>
          </div>
        </div>

        <!-- Description -->
        <p class="mb-6 leading-relaxed" style="color: var(--text-secondary);">${query.descricao}</p>

        <!-- Tables -->
        <div class="mb-6">
          <h4 class="text-xs font-semibold uppercase tracking-wider mb-3" style="color: var(--text-muted);">
            <svg class="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"/>
            </svg>
            Tabelas
          </h4>
          <div class="flex flex-wrap gap-2">${tablesHtml}</div>
        </div>

        <!-- Metrics & Dimensions -->
        <div class="grid grid-cols-2 gap-6 mb-6">
          <div>
            <h4 class="text-xs font-semibold uppercase tracking-wider mb-3" style="color: var(--text-muted);">
              <svg class="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
              </svg>
              Métricas
            </h4>
            <div class="flex flex-wrap gap-2">${metricsHtml}</div>
          </div>
          <div>
            <h4 class="text-xs font-semibold uppercase tracking-wider mb-3" style="color: var(--text-muted);">
              <svg class="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>
              </svg>
              Dimensões
            </h4>
            <div class="flex flex-wrap gap-2">${dimensionsHtml}</div>
          </div>
        </div>

        <!-- SQL Block -->
        <div class="sql-block rounded-xl overflow-hidden">
          <div class="sql-header px-4 py-3 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 rounded-full" style="background: #ff5f56;"></div>
              <div class="w-3 h-3 rounded-full" style="background: #ffbd2e;"></div>
              <div class="w-3 h-3 rounded-full" style="background: #27ca40;"></div>
              <span class="ml-3 text-xs font-mono" style="color: var(--text-muted);">SQL</span>
            </div>
            <button class="copy-btn px-3 py-1.5 rounded-lg text-xs font-medium transition-all hover:bg-opacity-80" 
                    style="background: var(--accent-blue); color: white;"
                    onclick="copySQL(${index})">
              <svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
              Copiar
            </button>
          </div>
          <div class="p-4 overflow-x-auto">
            <table class="font-mono text-sm w-full" style="color: var(--text-primary);">
              <tbody>${highlightedLines}</tbody>
            </table>
          </div>
        </div>
      </div>
    </article>
  `;
}

function renderNav(queries) {
  return queries.map((q, i) => `
    <a href="#query-${i + 1}" class="sidebar-item block px-4 py-3 rounded-lg border-l-2 border-transparent cursor-pointer">
      <div class="flex items-center gap-3">
        <span class="w-6 h-6 rounded-md flex items-center justify-center text-xs font-semibold" 
              style="background: var(--bg-elevated); color: var(--text-secondary);">${i + 1}</span>
        <div class="flex-1 min-w-0">
          <div class="text-sm font-medium truncate" style="color: var(--text-primary);">${q.titulo}</div>
          <div class="text-xs truncate" style="color: var(--text-muted);">${q.tipo}</div>
        </div>
      </div>
    </a>
  `).join('');
}

function filterQueries() {
  let filtered = sampleQueries;
  
  if (currentFilter !== 'all') {
    filtered = filtered.filter(q => q.tipo.toUpperCase() === currentFilter.toUpperCase());
  }
  
  if (searchTerm) {
    const term = searchTerm.toLowerCase();
    filtered = filtered.filter(q => 
      q.titulo.toLowerCase().includes(term) ||
      q.descricao.toLowerCase().includes(term) ||
      q.tabelas.some(t => t.toLowerCase().includes(term)) ||
      q.metricas.some(m => m.toLowerCase().includes(term))
    );
  }
  
  return filtered;
}

function renderAll() {
  const filtered = filterQueries();
  document.getElementById('cards-container').innerHTML = filtered.length 
    ? filtered.map((q, i) => renderCard(q, i + 1)).join('')
    : '<div class="text-center py-20"><p style="color: var(--text-muted);">Nenhuma query encontrada.</p></div>';
  
  document.getElementById('query-nav').innerHTML = renderNav(filtered);
  document.getElementById('total-queries').textContent = filtered.length;
  
  const allTables = [...new Set(filtered.flatMap(q => q.tabelas))];
  document.getElementById('total-tables').textContent = allTables.length;
}

function copySQL(index) {
  const query = filterQueries()[index - 1];
  if (query) {
    navigator.clipboard.writeText(query.sql).then(() => {
      const btn = event.target.closest('button');
      const originalText = btn.innerHTML;
      btn.innerHTML = '<svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>Copiado!';
      btn.style.background = 'var(--accent-emerald)';
      setTimeout(() => {
        btn.innerHTML = originalText;
        btn.style.background = 'var(--accent-blue)';
      }, 2000);
    });
  }
}

// Filter buttons
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => {
      b.style.background = 'var(--bg-elevated)';
      b.style.color = 'var(--text-secondary)';
    });
    btn.style.background = 'var(--accent-blue)';
    btn.style.color = 'white';
    
    currentFilter = btn.id.replace('filter-', '');
    renderAll();
  });
});

// Search
document.getElementById('search-input').addEventListener('input', (e) => {
  searchTerm = e.target.value;
  renderAll();
});

// Element SDK integration
async function onConfigChange(cfg) {
  const customFont = cfg.font_family || defaultConfig.font_family;
  
  document.getElementById('page-title').textContent = cfg.page_title || defaultConfig.page_title;
  document.getElementById('subtitle').textContent = cfg.subtitle || defaultConfig.subtitle;
  
  document.querySelectorAll('.font-display').forEach(el => {
    el.style.fontFamily = `${customFont}, system-ui, sans-serif`;
  });
}

function mapToCapabilities(cfg) {
  return {
    recolorables: [
      {
        get: () => cfg.bg_color || defaultConfig.bg_color,
        set: (v) => { cfg.bg_color = v; window.elementSdk.setConfig({ bg_color: v }); }
      },
      {
        get: () => cfg.primary_color || defaultConfig.primary_color,
        set: (v) => { cfg.primary_color = v; window.elementSdk.setConfig({ primary_color: v }); }
      },
      {
        get: () => cfg.text_color || defaultConfig.text_color,
        set: (v) => { cfg.text_color = v; window.elementSdk.setConfig({ text_color: v }); }
      }
    ],
    borderables: [],
    fontEditable: {
      get: () => cfg.font_family || defaultConfig.font_family,
      set: (v) => { cfg.font_family = v; window.elementSdk.setConfig({ font_family: v }); }
    },
    fontSizeable: {
      get: () => cfg.font_size || defaultConfig.font_size,
      set: (v) => { cfg.font_size = v; window.elementSdk.setConfig({ font_size: v }); }
    }
  };
}

function mapToEditPanelValues(cfg) {
  return new Map([
    ['page_title', cfg.page_title || defaultConfig.page_title],
    ['subtitle', cfg.subtitle || defaultConfig.subtitle]
  ]);
}

// Initialize
if (window.elementSdk) {
  window.elementSdk.init({
    defaultConfig,
    onConfigChange,
    mapToCapabilities,
    mapToEditPanelValues
  });
}

renderAll();

// Update timestamp
const now = new Date();
document.getElementById('generated-at').textContent = `Gerado em ${now.toLocaleDateString('pt-BR')} ${now.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}`;

// Particle system
function createParticles() {
  const particleCount = 30;
  const colors = ['var(--accent-blue)', 'var(--accent-purple)', 'var(--accent-cyan)'];
  
  for (let i = 0; i < particleCount; i++) {
    const particle = document.createElement('div');
    particle.className = 'particle';
    particle.style.left = Math.random() * 100 + '%';
    particle.style.background = colors[Math.floor(Math.random() * colors.length)];
    particle.style.animation = `float ${15 + Math.random() * 10}s linear infinite`;
    particle.style.animationDelay = Math.random() * 5 + 's';
    particle.style.width = particle.style.height = (1 + Math.random() * 2) + 'px';
    document.body.appendChild(particle);
  }
}

createParticles();

// Smooth scroll for sidebar navigation
document.addEventListener('click', (e) => {
  const link = e.target.closest('a[href^="#query-"]');
  if (link) {
    e.preventDefault();
    const targetId = link.getAttribute('href').substring(1);
    const target = document.getElementById(targetId);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      
      // Update active state
      document.querySelectorAll('.sidebar-item').forEach(item => item.classList.remove('active'));
      link.classList.add('active');
    }
  }
});

// Intersection Observer for active sidebar item
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const id = entry.target.id;
      document.querySelectorAll('.sidebar-item').forEach(item => {
        if (item.getAttribute('href') === `#${id}`) {
          document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
          item.classList.add('active');
        }
      });
    }
  });
}, { threshold: 0.5 });

// Observe all query cards
setTimeout(() => {
  document.querySelectorAll('[id^="query-"]').forEach(card => {
    observer.observe(card);
  });
}, 1000);
 (function(){function c(){var b=a.contentDocument||a.contentWindow.document;if(b){var d=b.createElement('script');d.innerHTML="window.__CF$cv$params={r:'9c186b32b0ea4f7e',t:'MTc2OTAxNTM2MC4wMDAwMDA='};var a=document.createElement('script');a.nonce='';a.src='/cdn-cgi/challenge-platform/scripts/jsd/main.js';document.getElementsByTagName('head')[0].appendChild(a);";b.getElementsByTagName('head')[0].appendChild(d)}}if(document.body){var a=document.createElement('iframe');a.height=1;a.width=1;a.style.position='absolute';a.style.top=0;a.style.left=0;a.style.border='none';a.style.visibility='hidden';document.body.appendChild(a);if('loading'!==document.readyState)c();else if(window.addEventListener)document.addEventListener('DOMContentLoaded',c);else{var e=document.onreadystatechange||function(){};document.onreadystatechange=function(b){e(b);'loading'!==document.readyState&&(document.onreadystatechange=e,c())}}}})();