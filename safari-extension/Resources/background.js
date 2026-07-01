const api = typeof browser !== 'undefined' ? browser : chrome;
const STORAGE_KEY = 'tabLog';

async function getLog() {
  const data = await api.storage.local.get(STORAGE_KEY);
  return data[STORAGE_KEY] || [];
}

async function saveLog(log) {
  await api.storage.local.set({ [STORAGE_KEY]: log });
}

function newEntry(tab) {
  return {
    entryId: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    tabId: tab.id,
    windowId: tab.windowId,
    url: tab.url || tab.pendingUrl || '',
    title: tab.title || '',
    description: '',
    openedAt: Date.now(),
    closedAt: null,
    status: 'open',
  };
}

// Ensure any tabs already open before the extension started tracking get logged.
async function syncExistingTabs() {
  const log = await getLog();
  const openTabs = await api.tabs.query({});
  const trackedOpenTabIds = new Set(
    log.filter((e) => e.status === 'open').map((e) => e.tabId)
  );
  let changed = false;
  for (const tab of openTabs) {
    if (!trackedOpenTabIds.has(tab.id)) {
      log.push(newEntry(tab));
      changed = true;
    }
  }
  if (changed) await saveLog(log);
}

api.runtime.onInstalled.addListener(() => {
  syncExistingTabs();
});
api.runtime.onStartup.addListener(() => {
  syncExistingTabs();
});

api.tabs.onCreated.addListener(async (tab) => {
  const log = await getLog();
  log.push(newEntry(tab));
  await saveLog(log);
});

api.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (!changeInfo.url && !changeInfo.title) return;
  const log = await getLog();
  let entry = log.find((e) => e.tabId === tabId && e.status === 'open');
  if (!entry) {
    entry = newEntry(tab);
    log.push(entry);
  }
  if (changeInfo.url) entry.url = changeInfo.url;
  if (changeInfo.title) entry.title = changeInfo.title;
  await saveLog(log);
});

api.tabs.onRemoved.addListener(async (tabId) => {
  const log = await getLog();
  const entry = log.find((e) => e.tabId === tabId && e.status === 'open');
  if (entry) {
    entry.closedAt = Date.now();
    entry.status = 'closed';
    await saveLog(log);
  }
});

api.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === 'PAGE_INFO' && sender.tab) {
    (async () => {
      const log = await getLog();
      const entry = log.find((e) => e.tabId === sender.tab.id && e.status === 'open');
      if (entry) {
        if (message.description) entry.description = message.description;
        if (message.title) entry.title = message.title;
        if (message.url) entry.url = message.url;
        await saveLog(log);
      }
      sendResponse({ ok: true });
    })();
    return true; // keep channel open for async sendResponse
  }
});
