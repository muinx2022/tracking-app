(function () {
  "use strict";

  var script = document.currentScript;
  if (!script) return;
  var trackingId = script.getAttribute("data-tracking-id");
  if (!trackingId) return;

  var scriptUrl;
  try {
    scriptUrl = new URL(script.src);
  } catch (e) {
    return;
  }

  var origin = scriptUrl.origin;
  var endpoint = origin + "/api/track/";
  var SESSION_MS = 30 * 60 * 1000;
  var ENGAGED_THRESHOLD_MS = 15000;
  var SCROLL_MILESTONES = [25, 50, 75, 100];
  var clientKey = "ta_cid_" + trackingId;
  var sessionKey = "ta_sid_" + trackingId;
  var sessionTimeKey = "ta_sid_t_" + trackingId;
  var sentEngaged = false;
  var sentExit = false;
  var sentScroll = {};
  var pageStartedAt = Date.now();

  function randomId() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      var v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function getClientId() {
    try {
      var v = localStorage.getItem(clientKey);
      if (!v) {
        v = randomId();
        localStorage.setItem(clientKey, v);
      }
      return v;
    } catch (err) {
      return randomId();
    }
  }

  function getSessionId() {
    try {
      var sid = sessionStorage.getItem(sessionKey);
      var last = parseInt(sessionStorage.getItem(sessionTimeKey) || "0", 10);
      var now = Date.now();
      if (!sid || !last || now - last > SESSION_MS) sid = randomId();
      sessionStorage.setItem(sessionKey, sid);
      sessionStorage.setItem(sessionTimeKey, String(now));
      return sid;
    } catch (err) {
      return randomId();
    }
  }

  function getMeta(name) {
    var node = document.querySelector('meta[name="' + name + '"]');
    return node ? node.getAttribute("content") || "" : "";
  }

  function getTags() {
    var raw = getMeta("trekky:tags");
    if (!raw) return [];
    return raw.split(",").map(function (v) { return v.trim(); }).filter(Boolean).slice(0, 20);
  }

  function getUtmParams() {
    var params = new URLSearchParams(window.location.search);
    return {
      utm_source: params.get("utm_source") || "",
      utm_medium: params.get("utm_medium") || "",
      utm_campaign: params.get("utm_campaign") || "",
      utm_content: params.get("utm_content") || "",
      utm_term: params.get("utm_term") || ""
    };
  }

  function basePayload() {
    var utm = getUtmParams();
    return {
      tracking_id: trackingId,
      client_id: getClientId(),
      session_id: getSessionId(),
      url: window.location.href,
      title: document.title || "",
      referrer: document.referrer || "",
      occurred_at: new Date().toISOString(),
      screen_width: window.screen ? window.screen.width : null,
      screen_height: window.screen ? window.screen.height : null,
      language: navigator.language || "",
      page_type: getMeta("trekky:page_type"),
      content_id: getMeta("trekky:content_id"),
      content_slug: getMeta("trekky:content_slug"),
      content_title: getMeta("trekky:content_title") || document.title || "",
      author: getMeta("trekky:author"),
      category: getMeta("trekky:category"),
      tags: getTags(),
      utm_source: utm.utm_source,
      utm_medium: utm.utm_medium,
      utm_campaign: utm.utm_campaign,
      utm_content: utm.utm_content,
      utm_term: utm.utm_term
    };
  }

  function send(payload, useBeacon) {
    var body = JSON.stringify(payload);
    if (useBeacon && navigator.sendBeacon) {
      try {
        var blob = new Blob([body], { type: "application/json" });
        if (navigator.sendBeacon(endpoint, blob)) return;
      } catch (err) {}
    }
    fetch(endpoint, {
      method: "POST",
      body: body,
      headers: { "Content-Type": "application/json" },
      mode: "cors",
      credentials: "omit",
      keepalive: true
    }).catch(function () {});
  }

  function trackEvent(eventType, extras, useBeacon) {
    var payload = basePayload();
    payload.event_type = eventType;
    extras = extras || {};
    for (var key in extras) payload[key] = extras[key];
    send(payload, !!useBeacon);
  }

  function trackPageview() {
    sentEngaged = false;
    sentExit = false;
    sentScroll = {};
    pageStartedAt = Date.now();
    trackEvent("pageview");
  }

  function maybeTrackEngaged() {
    if (sentEngaged) return;
    var engagedSeconds = Math.round((Date.now() - pageStartedAt) / 1000);
    if (engagedSeconds < ENGAGED_THRESHOLD_MS / 1000) return;
    sentEngaged = true;
    trackEvent("engaged_visit", { engaged_seconds: engagedSeconds });
  }

  function trackExit() {
    if (sentExit) return;
    sentExit = true;
    trackEvent("page_exit", { engaged_seconds: Math.round((Date.now() - pageStartedAt) / 1000) }, true);
  }

  function maxScrollPercent() {
    var doc = document.documentElement;
    var body = document.body;
    var height = Math.max(
      body.scrollHeight, body.offsetHeight, doc.clientHeight, doc.scrollHeight, doc.offsetHeight
    );
    var win = window.innerHeight || doc.clientHeight || 0;
    if (!height || height <= win) return 100;
    var top = window.scrollY || window.pageYOffset || doc.scrollTop || 0;
    return Math.max(0, Math.min(100, Math.round(((top + win) / height) * 100)));
  }

  function handleScroll() {
    var percent = maxScrollPercent();
    SCROLL_MILESTONES.forEach(function (milestone) {
      if (percent >= milestone && !sentScroll[milestone]) {
        sentScroll[milestone] = true;
        trackEvent("scroll_depth", { scroll_percent: milestone });
      }
    });
  }

  function handleCtaClick(event) {
    var el = event.target && event.target.closest ? event.target.closest("[data-track-cta], a[href]") : null;
    if (!el) return;
    var href = el.getAttribute("href") || "";
    var isInternal = !!href && href.charAt(0) === "/";
    var isTracked = el.hasAttribute("data-track-cta") || isInternal;
    if (!isTracked) return;
    trackEvent("cta_click", {
      destination_url: href,
      cta_name: el.getAttribute("data-track-cta") || el.textContent.trim().slice(0, 255),
      properties: {
        tag_name: el.tagName.toLowerCase(),
        text: (el.textContent || "").trim().slice(0, 255)
      }
    });
  }

  window.TrekkyTrack = {
    track: function (name, properties) {
      trackEvent("custom", {
        event_name: String(name || "").slice(0, 128),
        properties: properties && typeof properties === "object" ? properties : {}
      });
    },
    pageview: trackPageview
  };

  trackPageview();

  var pushState = history.pushState;
  history.pushState = function () {
    var ret = pushState.apply(history, arguments);
    trackPageview();
    return ret;
  };
  var replaceState = history.replaceState;
  history.replaceState = function () {
    var ret = replaceState.apply(history, arguments);
    trackPageview();
    return ret;
  };

  window.addEventListener("popstate", trackPageview);
  window.addEventListener("scroll", handleScroll, { passive: true });
  window.addEventListener("click", handleCtaClick, true);
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") {
      maybeTrackEngaged();
      trackExit();
    }
  });
  window.addEventListener("beforeunload", trackExit);
  window.setInterval(maybeTrackEngaged, 5000);
})();
