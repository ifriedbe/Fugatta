const api = typeof browser !== 'undefined' ? browser : chrome;
const STORAGE_KEY = 'tabLog';

const statOpenEl = document.getElementById('stat-open');
const statClosedEl = document.getElementById('stat-closed');
const statTotalEl = document.getElementById('stat-total');
const previewBody = document.getElementById('preview-body');
const statusEl = document.getElementById('status');
const exportBtn = document.getElementById('export-btn');
const clearBtn = document.getElementById('clear-btn');

function fmtTime(ms) {
  if (!ms) return '—';
  const d = new Date(ms);
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function fmtDuration(openedAt, closedAt) {
  const end = closedAt || Date.now();
  const ms = Math.max(0, end - openedAt);
  const totalMin = Math.round(ms / 60000);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

async function getLog() {
  const data = await api.storage.local.get(STORAGE_KEY);
  return (data[STORAGE_KEY] || []).slice().sort((a, b) => b.openedAt - a.openedAt);
}

function setStatus(msg, isError) {
  statusEl.textContent = msg;
  statusEl.style.color = isError ? '#b91c1c' : '';
}

async function render() {
  const log = await getLog();
  const openCount = log.filter((e) => e.status === 'open').length;
  const closedCount = log.length - openCount;
  statOpenEl.textContent = openCount;
  statClosedEl.textContent = closedCount;
  statTotalEl.textContent = log.length;

  previewBody.innerHTML = '';
  for (const entry of log.slice(0, 30)) {
    const tr = document.createElement('tr');
    const title = entry.title || entry.url || '(untitled)';
    tr.innerHTML = `
      <td title="${escapeHtml(entry.url)}">${escapeHtml(title)}</td>
      <td>${fmtTime(entry.openedAt)}</td>
      <td>${entry.status === 'open' ? 'still open' : fmtTime(entry.closedAt)}</td>
    `;
    previewBody.appendChild(tr);
  }
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}

async function exportToExcel() {
  exportBtn.disabled = true;
  setStatus('Building workbook…');
  try {
    const log = await getLog();
    if (log.length === 0) {
      setStatus('No tabs logged yet.', true);
      return;
    }

    const workbook = new ExcelJS.Workbook();
    workbook.creator = 'Tab Logbook';
    workbook.created = new Date();

    const sheet = workbook.addWorksheet('Tab Log', {
      views: [{ state: 'frozen', ySplit: 1 }],
    });

    sheet.columns = [
      { header: 'Title', key: 'title', width: 38 },
      { header: 'URL', key: 'url', width: 45 },
      { header: 'Description', key: 'description', width: 50 },
      { header: 'Opened At', key: 'openedAt', width: 20 },
      { header: 'Closed At', key: 'closedAt', width: 20 },
      { header: 'Duration', key: 'duration', width: 12 },
      { header: 'Status', key: 'status', width: 12 },
    ];

    const headerRow = sheet.getRow(1);
    headerRow.height = 22;
    headerRow.eachCell((cell) => {
      cell.font = { bold: true, color: { argb: 'FFFFFFFF' }, size: 11 };
      cell.fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: 'FF0F766E' },
      };
      cell.alignment = { vertical: 'middle', horizontal: 'left' };
      cell.border = { bottom: { style: 'thin', color: { argb: 'FF0B5750' } } };
    });

    log.forEach((entry) => {
      const row = sheet.addRow({
        title: entry.title || '(untitled)',
        url: entry.url,
        description: entry.description || '',
        openedAt: entry.openedAt ? new Date(entry.openedAt) : null,
        closedAt: entry.closedAt ? new Date(entry.closedAt) : null,
        duration: fmtDuration(entry.openedAt, entry.closedAt),
        status: entry.status === 'open' ? 'Still open' : 'Closed',
      });

      row.getCell('openedAt').numFmt = 'yyyy-mm-dd hh:mm';
      row.getCell('closedAt').numFmt = 'yyyy-mm-dd hh:mm';
      row.getCell('url').font = { color: { argb: 'FF1D4ED8' }, underline: true };
      if (entry.url) {
        row.getCell('url').value = { text: entry.url, hyperlink: entry.url };
      }
      row.getCell('description').alignment = { wrapText: true, vertical: 'top' };
      row.eachCell((cell) => {
        cell.border = { bottom: { style: 'thin', color: { argb: 'FFE5E7EB' } } };
        cell.alignment = { ...cell.alignment, vertical: 'top', wrapText: cell.alignment?.wrapText || false };
      });

      const statusCell = row.getCell('status');
      statusCell.font = { bold: true, color: { argb: entry.status === 'open' ? 'FF15803D' : 'FF6B7280' } };
    });

    // Alternate row banding for readability.
    for (let i = 2; i <= sheet.rowCount; i++) {
      if (i % 2 === 0) {
        sheet.getRow(i).eachCell((cell) => {
          if (!cell.fill || cell.fill.type !== 'pattern') {
            cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF3F4F6' } };
          }
        });
      }
    }

    sheet.autoFilter = { from: 'A1', to: 'G1' };

    const buffer = await workbook.xlsx.writeBuffer();
    const blob = new Blob([buffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const url = URL.createObjectURL(blob);
    const filename = `tab-log-${new Date().toISOString().slice(0, 10)}.xlsx`;

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);

    setStatus(`Exported ${log.length} tabs to ${filename}`);
  } catch (err) {
    console.error(err);
    setStatus('Export failed: ' + err.message, true);
  } finally {
    exportBtn.disabled = false;
  }
}

async function clearLog() {
  if (!confirm('Clear the entire tab log? This cannot be undone.')) return;
  await api.storage.local.set({ [STORAGE_KEY]: [] });
  await render();
  setStatus('Log cleared.');
}

exportBtn.addEventListener('click', exportToExcel);
clearBtn.addEventListener('click', clearLog);

render();
api.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes[STORAGE_KEY]) render();
});
