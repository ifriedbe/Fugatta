(function () {
  const api = typeof browser !== 'undefined' ? browser : chrome;

  function getDescription() {
    const meta =
      document.querySelector('meta[name="description"]') ||
      document.querySelector('meta[property="og:description"]');
    return meta ? meta.content.trim() : '';
  }

  function report() {
    api.runtime.sendMessage({
      type: 'PAGE_INFO',
      url: location.href,
      title: document.title,
      description: getDescription(),
    });
  }

  report();
  // Re-report if the title changes later (e.g. SPA navigation, async page title updates).
  const observer = new MutationObserver(() => report());
  const titleEl = document.querySelector('title');
  if (titleEl) observer.observe(titleEl, { childList: true });
})();
