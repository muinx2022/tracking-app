(function () {
  "use strict";

  var script = document.currentScript;
  if (!script) {
    return;
  }

  var trackingId = script.getAttribute("data-tracking-id");
  if (!trackingId) {
    return;
  }

  try {
    var scriptUrl = new URL(script.src);
    var origin = scriptUrl.origin;
  } catch (e) {
    return;
  }

  var endpoint = origin + "/api/track/";

  function randomId() {
    if (window.crypto && window.crypto.randomUUID) {
      return window.crypto.randomUUID();
    }
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      var v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  var clientKey = "ta_cid_" + trackingId;
  var sessionKey = "ta_sid_" + trackingId;
  var sessionTimeKey = "ta_sid_t_" + trackingId;

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

  var SESSION_MS = 30 * 60 * 1000;

  function getSessionId() {
    try {
      var sid = sessionStorage.getItem(sessionKey);
      var last = parseInt(sessionStorage.getItem(sessionTimeKey) || "0", 10);
      var now = Date.now();
      if (!sid || !last || now - last > SESSION_MS) {
        sid = randomId();
      }
      sessionStorage.setItem(sessionKey, sid);
      sessionStorage.setItem(sessionTimeKey, String(now));
      return sid;
    } catch (err) {
      return randomId();
    }
  }

  function sendPageview(url, title, referrer) {
    var payload = {
      tracking_id: trackingId,
      client_id: getClientId(),
      session_id: getSessionId(),
      event_type: "pageview",
      url: url || window.location.href,
      title: title || document.title || "",
      referrer: referrer || (document.referrer || ""),
      occurred_at: new Date().toISOString(),
      screen_width: window.screen ? window.screen.width : null,
      screen_height: window.screen ? window.screen.height : null,
      language: navigator.language || "",
    };

    var body = JSON.stringify(payload);
    var ok = false;
    if (navigator.sendBeacon) {
      try {
        var blob = new Blob([body], { type: "application/json" });
        ok = navigator.sendBeacon(endpoint, blob);
      } catch (err) {
        ok = false;
      }
    }
    if (!ok) {
      fetch(endpoint, {
        method: "POST",
        body: body,
        headers: { "Content-Type": "application/json" },
        mode: "cors",
        credentials: "omit",
        keepalive: true,
      }).catch(function () {});
    }
  }

  sendPageview();

  var pushState = history.pushState;
  history.pushState = function () {
    var ret = pushState.apply(history, arguments);
    sendPageview();
    return ret;
  };

  window.addEventListener("popstate", function () {
    sendPageview();
  });

  var replaceState = history.replaceState;
  history.replaceState = function () {
    var ret = replaceState.apply(history, arguments);
    sendPageview();
    return ret;
  };
})();
