(function () {
  var TOUR_STORAGE_KEY = 'must_emr_tours';
  var activeTour = null;
  var currentStep = 0;
  var overlayEl = null;
  var tooltipEl = null;
  var highlightEl = null;

  function getTourState() {
    try { return JSON.parse(localStorage.getItem(TOUR_STORAGE_KEY)) || {}; } catch (_) { return {}; }
  }

  function setTourDone(tourId) {
    var state = getTourState();
    state[tourId] = true;
    localStorage.setItem(TOUR_STORAGE_KEY, JSON.stringify(state));
  }

  function isTourDone(tourId) {
    return !!getTourState()[tourId];
  }

  function createOverlay() {
    if (overlayEl) return;
    overlayEl = document.createElement('div');
    overlayEl.id = 'st-tour-overlay';
    overlayEl.style.cssText = 'position:fixed;inset:0;z-index:99998;background:rgba(0,0,0,0.45);transition:opacity 0.25s';
    document.body.appendChild(overlayEl);

    highlightEl = document.createElement('div');
    highlightEl.id = 'st-tour-highlight';
    highlightEl.style.cssText = 'position:fixed;z-index:99999;border-radius:4px;box-shadow:0 0 0 9999px rgba(0,0,0,0.45);transition:all 0.25s ease;pointer-events:none';
    document.body.appendChild(highlightEl);

    tooltipEl = document.createElement('div');
    tooltipEl.id = 'st-tour-tooltip';
    tooltipEl.style.cssText = 'position:fixed;z-index:100000;background:#fff;border:1px solid #d7e3dd;box-shadow:0 12px 40px rgba(0,0,0,0.18);max-width:380px;width:90vw;padding:0;transition:opacity 0.2s,transform 0.2s';
    document.body.appendChild(tooltipEl);
  }

  function removeOverlay() {
    if (overlayEl) { overlayEl.remove(); overlayEl = null; }
    if (highlightEl) { highlightEl.remove(); highlightEl = null; }
    if (tooltipEl) { tooltipEl.remove(); tooltipEl = null; }
  }

  function getElement(selector) {
    if (typeof selector === 'string') return document.querySelector(selector);
    return selector;
  }

  function getRect(el) {
    if (!el || !el.getBoundingClientRect) return { top: 0, left: 0, width: 0, height: 0 };
    return el.getBoundingClientRect();
  }

  function showStep(step) {
    if (!tooltipEl || !highlightEl) return;
    var target = getElement(step.element);
    if (!target) {
      tooltipEl.style.opacity = '0';
      return;
    }
    target.scrollIntoView({ block: 'center', behavior: 'smooth' });

    var scrollPause = Math.min(100 + window.scrollY * 0.3, 600);

    setTimeout(function () {
      var rect = getRect(target);
      if (!rect || rect.width === 0) { tooltipEl.style.opacity = '0'; return; }

      var pad = 6;
      highlightEl.style.top = (rect.top - pad) + 'px';
      highlightEl.style.left = (rect.left - pad) + 'px';
      highlightEl.style.width = (rect.width + pad * 2) + 'px';
      highlightEl.style.height = (rect.height + pad * 2) + 'px';
      highlightEl.style.opacity = '1';

      var placement = step.placement || 'bottom';
      var tipW = Math.min(380, window.innerWidth - 32);
      var tipH = 180;
      var vw = window.innerWidth;
      var vh = window.innerHeight;
      var cx = rect.left + rect.width / 2;
      var cy = rect.top + rect.height / 2;

      var tx, ty;
      if (placement === 'bottom') {
        tx = Math.max(16, Math.min(cx - tipW / 2, vw - tipW - 16));
        ty = rect.bottom + pad + 12;
        if (ty + tipH > vh) { placement = 'top'; }
      }
      if (placement === 'top') {
        tx = Math.max(16, Math.min(cx - tipW / 2, vw - tipW - 16));
        ty = rect.top - tipH - pad - 12;
        if (ty < 0) { placement = 'bottom'; ty = rect.bottom + pad + 12; }
      }
      if (placement === 'left') {
        ty = Math.max(16, Math.min(cy - tipH / 2, vh - tipH - 16));
        tx = rect.left - tipW - pad - 12;
        if (tx < 0) { placement = 'right'; tx = rect.right + pad + 12; }
      }
      if (placement === 'right') {
        ty = Math.max(16, Math.min(cy - tipH / 2, vh - tipH - 16));
        tx = rect.right + pad + 12;
        if (tx + tipW > vw) { placement = 'left'; tx = rect.left - tipW - pad - 12; }
      }

      var arrowDir = placement;
      var arrowStyles = {
        bottom: 'top:-8px;left:50%;transform:translateX(-50%);border-left:8px solid transparent;border-right:8px solid transparent;border-bottom:8px solid #fff',
        top: 'bottom:-8px;left:50%;transform:translateX(-50%);border-left:8px solid transparent;border-right:8px solid transparent;border-top:8px solid #fff',
        left: 'right:-8px;top:50%;transform:translateY(-50%);border-top:8px solid transparent;border-bottom:8px solid transparent;border-left:8px solid #fff',
        right: 'left:-8px;top:50%;transform:translateY(-50%);border-top:8px solid transparent;border-bottom:8px solid transparent;border-right:8px solid #fff',
      };

      tooltipEl.style.left = tx + 'px';
      tooltipEl.style.top = ty + 'px';
      tooltipEl.style.opacity = '1';
      tooltipEl.style.transform = 'translateY(0)';

      var isLast = currentStep === activeTour.steps.length - 1;
      var isFirst = currentStep === 0;
      var total = activeTour.steps.length;

      tooltipEl.innerHTML =
        '<div style="position:relative;padding:20px 24px 16px">' +
          '<button data-st-close style="position:absolute;top:8px;right:10px;border:0;background:0;font-size:18px;line-height:1;color:#9ca3af;cursor:pointer;padding:4px">&times;</button>' +
          '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">' +
            '<span style="background:#0b5144;color:#fff;font:700 10px/1 ui-sans-serif,system-ui,sans-serif;padding:2px 7px;letter-spacing:.04em">' + (currentStep + 1) + '/' + total + '</span>' +
            '<span style="font:700 13px/1.2 ui-sans-serif,system-ui,sans-serif;color:#1f2937">' + escapeHtml(step.title) + '</span>' +
          '</div>' +
          '<p style="margin:8px 0 0;font:14px/1.5 ui-sans-serif,system-ui,sans-serif;color:#4b5563">' + escapeHtml(step.content) + '</p>' +
          '<div style="display:flex;align-items:center;justify-content:space-between;margin-top:14px;padding-top:12px;border-top:1px solid #e5e7eb">' +
            '<button data-st-prev style="border:0;background:0;color:#6b7280;font:600 12px/1 ui-sans-serif,system-ui,sans-serif;cursor:pointer;padding:6px 0' + (isFirst ? ';visibility:hidden' : '') + '">\u2190 Back</button>' +
            '<div style="display:flex;gap:6px">' +
              '<button data-st-skip style="border:1px solid #d1d5db;background:#fff;color:#374151;font:600 12px/1 ui-sans-serif,system-ui,sans-serif;padding:7px 12px;cursor:pointer">Skip</button>' +
              (isLast
                ? '<button data-st-finish style="border:0;background:#0b5144;color:#fff;font:700 12px/1 ui-sans-serif,system-ui,sans-serif;padding:7px 14px;cursor:pointer">Done</button>'
                : '<button data-st-next style="border:0;background:#0b5144;color:#fff;font:700 12px/1 ui-sans-serif,system-ui,sans-serif;padding:7px 14px;cursor:pointer">Next \u2192</button>') +
            '</div>' +
          '</div>' +
          '<div style="position:absolute;' + arrowStyles[arrowDir] + '"></div>' +
        '</div>';

      tooltipEl.querySelector('[data-st-close]').addEventListener('click', endTour);
      tooltipEl.querySelector('[data-st-skip]').addEventListener('click', endTour);
      tooltipEl.querySelector('[data-st-prev]')?.addEventListener('click', function () { if (currentStep > 0) { currentStep--; showStep(activeTour.steps[currentStep]); } });
      if (isLast) {
        tooltipEl.querySelector('[data-st-finish]').addEventListener('click', endTour);
      } else {
        tooltipEl.querySelector('[data-st-next]').addEventListener('click', function () { if (currentStep < activeTour.steps.length - 1) { currentStep++; showStep(activeTour.steps[currentStep]); } });
      }
    }, 400);
  }

  function startTour(tour) {
    if (!tour || !tour.steps || !tour.steps.length) return;
    activeTour = tour;
    currentStep = 0;
    createOverlay();
    overlayEl.style.opacity = '1';
    showStep(tour.steps[0]);
  }

  function endTour() {
    if (activeTour) {
      setTourDone(activeTour.id);
    }
    removeOverlay();
    activeTour = null;
    currentStep = 0;
  }

  function escapeHtml(text) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
  }

  window.SystemTour = {
    start: function (tour) { startTour(tour); },
    end: endTour,
    isDone: isTourDone,
    markDone: setTourDone,
    autoStart: function (tour) {
      if (!isTourDone(tour.id)) {
        setTimeout(function () { startTour(tour); }, 600);
      }
    },
  };
})();
