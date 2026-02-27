"use client";
// Inspector Bridge Script - Client Component for Next.js App Router
// Version: 2.3
import { useEffect } from "react";

declare global {
  interface Window {
    __inspectorBridgeLoaded?: boolean;
    __NEXT_PUBLIC_API_URL__?: string;
  }
}

interface BridgeMessage {
  type: string;
  action?: string;
  elementInfo?: string;
  position?: { xPercent: number; yPercent: number };
  pageUrl?: string;
  timestamp?: number;
  level?: string | null;
  source?: string;
  role?: string;
  isInIframe?: boolean;
  command?: string;
  selector?: string;
  url?: string;
  title?: string;
}

function getWsUrl(): string {
  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL ||
    (typeof window !== "undefined" ? window.__NEXT_PUBLIC_API_URL__ : null) ||
    "http://localhost:8000";
  const wsProtocol = apiUrl.startsWith("https") ? "wss" : "ws";
  const wsHost = apiUrl.replace(/^https?:\/\//, "");
  const channel =
    process.env.NEXT_PUBLIC_INSPECTOR_CHANNEL ||
    "gh_mahdighandi1989_project_management";
  return `${wsProtocol}://${wsHost}/api/render/ws/bridge/${channel}`;
}

export default function InspectorBridge() {
  useEffect(() => {
    if (typeof window === "undefined" || window.__inspectorBridgeLoaded) return;
    window.__inspectorBridgeLoaded = true;

    const isInIframe = window !== window.parent;
    const WS_URL = getWsUrl();
    let ws: WebSocket | null = null;
    let wsReady = false;
    let messageQueue: BridgeMessage[] = [];

    console.log("Inspector Bridge: Active (WebSocket mode)");

    // Debounce
    const DEBOUNCE_MS = 100;
    let lastEventTime = 0;
    const shouldSend = () => {
      const now = Date.now();
      if (now - lastEventTime < DEBOUNCE_MS) return false;
      lastEventTime = now;
      return true;
    };

    // WebSocket connection
    const connectWS = () => {
      if (!WS_URL) return;
      try {
        ws = new WebSocket(WS_URL);
        ws.onopen = () => {
          ws?.send(JSON.stringify({ type: "register", role: "bridge" }));
        };
        ws.onmessage = (event: MessageEvent) => {
          try {
            const msg = JSON.parse(event.data) as BridgeMessage;
            if (msg.type === "registered") {
              wsReady = true;
              console.log("Inspector Bridge: WebSocket connected");
              messageQueue.forEach((m) => ws?.send(JSON.stringify(m)));
              messageQueue = [];
              ws?.send(
                JSON.stringify({
                  type: "inspector-bridge-ready",
                  pageUrl: window.location.href,
                  isInIframe,
                  timestamp: Date.now(),
                })
              );
            } else if (msg.type === "command") {
              handleCommand(msg);
            }
          } catch (_e) {
            // ignore parse errors
          }
        };
        ws.onclose = () => {
          wsReady = false;
          setTimeout(connectWS, 3000);
        };
        ws.onerror = () => {
          // silent reconnect handled by onclose
        };
      } catch (_e) {
        // WebSocket creation failed
      }
    };

    const handleCommand = (msg: BridgeMessage) => {
      if (msg.command === "click") {
        const el = msg.selector
          ? document.querySelector(msg.selector)
          : null;
        if (el instanceof HTMLElement) el.click();
      } else if (msg.command === "navigate") {
        if (msg.url) window.location.href = msg.url;
      } else if (msg.command === "get-elements") {
        const elements: Array<{
          index: number;
          tag: string;
          text: string;
          id: string;
          href: string;
        }> = [];
        document
          .querySelectorAll(
            "a, button, input, textarea, select, [role=button]"
          )
          .forEach((el, i) => {
            const htmlEl = el as HTMLElement & { value?: string; href?: string };
            elements.push({
              index: i,
              tag: el.tagName.toLowerCase(),
              text: (htmlEl.innerText || htmlEl.value || "").trim().slice(0, 50),
              id: el.id,
              href: htmlEl.href || "",
            });
          });
        sendToInspector("elements-list", { elementInfo: JSON.stringify(elements) });
      }
    };

    const sendToInspector = (
      action: string,
      data: {
        elementInfo?: string;
        position?: { xPercent: number; yPercent: number };
        level?: string | null;
      }
    ) => {
      const message: BridgeMessage = {
        type: "inspector-bridge-event",
        action,
        elementInfo: data.elementInfo || "",
        position: data.position || { xPercent: 50, yPercent: 50 },
        pageUrl: window.location.href,
        timestamp: Date.now(),
        level: data.level || null,
        source: "imported-project",
      };
      if (ws && wsReady) ws.send(JSON.stringify(message));
      else if (ws) messageQueue.push(message);
      if (isInIframe) {
        try {
          window.parent.postMessage(message, "*");
        } catch (_e) {
          // cross-origin postMessage failed
        }
      }
    };

    const getElementInfo = (el: EventTarget | null): string => {
      if (!el || !(el instanceof HTMLElement)) return "";
      const htmlEl = el as HTMLElement & { value?: string };
      const text = (htmlEl.innerText || htmlEl.value || "").trim().slice(0, 50);
      const tag = htmlEl.tagName?.toLowerCase() || "";
      const id = htmlEl.id ? "#" + htmlEl.id : "";
      const cls =
        htmlEl.className && typeof htmlEl.className === "string"
          ? "." + htmlEl.className.split(" ")[0]
          : "";
      const tagLabels: Record<string, string> = {
        button: "\u062F\u06A9\u0645\u0647",
        a: "\u0644\u06CC\u0646\u06A9",
        input: "\u0641\u06CC\u0644\u062F \u0648\u0631\u0648\u062F\u06CC",
        textarea: "\u0641\u06CC\u0644\u062F \u0645\u062A\u0646",
        select: "\u0645\u0646\u0648\u06CC \u0627\u0646\u062A\u062E\u0627\u0628",
        img: "\u062A\u0635\u0648\u06CC\u0631",
        form: "\u0641\u0631\u0645",
        div: "\u0628\u062E\u0634",
        span: "\u0645\u062A\u0646",
        p: "\u067E\u0627\u0631\u0627\u06AF\u0631\u0627\u0641",
        h1: "\u0639\u0646\u0648\u0627\u0646 \u0627\u0635\u0644\u06CC",
        h2: "\u0639\u0646\u0648\u0627\u0646",
        h3: "\u0639\u0646\u0648\u0627\u0646",
        nav: "\u0645\u0646\u0648\u06CC \u0646\u0627\u0648\u0628\u0631\u06CC",
        header: "\u0633\u0631\u0628\u0631\u06AF",
        footer: "\u067E\u0627\u0648\u0631\u0642\u06CC",
        li: "\u0622\u06CC\u062A\u0645 \u0644\u06CC\u0633\u062A",
        table: "\u062C\u062F\u0648\u0644",
        video: "\u0648\u06CC\u062F\u06CC\u0648",
      };
      const typeLabel = tagLabels[tag] || tag;
      if (text) return `${typeLabel} "${text}"`;
      return typeLabel + (id || cls || "");
    };

    const getPositionPercent = (e: MouseEvent | PointerEvent) => ({
      xPercent: (e.clientX / window.innerWidth) * 100,
      yPercent: (e.clientY / window.innerHeight) * 100,
    });

    // Window capture phase event handlers
    const handleClick = (e: MouseEvent) => {
      if (!shouldSend()) return;
      sendToInspector("click", {
        elementInfo: getElementInfo(e.target),
        position: getPositionPercent(e),
      });
    };
    const handleInput = (e: Event) => {
      if (!shouldSend()) return;
      const target = e.target as HTMLElement | null;
      if (target?.tagName === "INPUT" || target?.tagName === "TEXTAREA") {
        sendToInspector("input", { elementInfo: getElementInfo(target) });
      }
    };
    const handleFocus = (e: FocusEvent) => {
      if (!shouldSend()) return;
      if (e.target && e.target !== document && e.target !== document.body) {
        sendToInspector("focus", { elementInfo: getElementInfo(e.target) });
      }
    };
    let scrollTimeout: ReturnType<typeof setTimeout>;
    const handleScroll = () => {
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        sendToInspector("scroll", {
          elementInfo: "\u0635\u0641\u062D\u0647",
        });
      }, 200);
    };

    window.addEventListener("click", handleClick, true);
    window.addEventListener("input", handleInput, true);
    window.addEventListener("scroll", handleScroll, true);
    window.addEventListener("focus", handleFocus, true);

    // Fallback pointerdown
    const handlePointerDown = (e: PointerEvent) => {
      setTimeout(() => {
        if (Date.now() - lastEventTime > 180) {
          sendToInspector("click", {
            elementInfo: getElementInfo(e.target) + " (pointerdown)",
            position: getPositionPercent(e),
          });
        }
      }, 200);
    };
    window.addEventListener("pointerdown", handlePointerDown, true);

    // URL change tracking (SPA navigation)
    let _lastKnownUrl = window.location.href;
    const _notifyUrlChange = () => {
      const cur = window.location.href;
      if (cur !== _lastKnownUrl) {
        _lastKnownUrl = cur;
        sendToInspector("url-changed", { elementInfo: cur });
        if (isInIframe) {
          try {
            window.parent.postMessage(
              {
                type: "inspector-url-changed",
                pageUrl: cur,
                timestamp: Date.now(),
              },
              "*"
            );
          } catch (_e) {
            // cross-origin
          }
        }
      }
    };
    window.addEventListener("popstate", _notifyUrlChange);
    window.addEventListener("hashchange", _notifyUrlChange);
    // Intercept pushState/replaceState (SPA frameworks use these without firing events)
    const _origPushState = history.pushState;
    const _origReplaceState = history.replaceState;
    history.pushState = function (...args: Parameters<typeof _origPushState>) {
      _origPushState.apply(this, args);
      setTimeout(_notifyUrlChange, 50);
    };
    history.replaceState = function (
      ...args: Parameters<typeof _origReplaceState>
    ) {
      _origReplaceState.apply(this, args);
      setTimeout(_notifyUrlChange, 50);
    };
    // Periodic fallback (some frameworks bypass history API)
    const _urlCheckInterval = setInterval(_notifyUrlChange, 1500);

    // Console interception
    let consoleLogCount = 0;
    const MAX_CONSOLE_LOGS = 200;

    type ConsoleFn = (...args: unknown[]) => void;

    const interceptConsole =
      (level: string, origFn: ConsoleFn): ConsoleFn =>
      (...args: unknown[]) => {
        origFn.apply(console, args);
        if (consoleLogCount >= MAX_CONSOLE_LOGS) return;
        consoleLogCount++;
        const msg = args
          .map((a) =>
            typeof a === "object"
              ? JSON.stringify(a).slice(0, 200)
              : String(a).slice(0, 200)
          )
          .join(" ")
          .slice(0, 500);
        if (msg.includes("Inspector Bridge")) return;
        sendToInspector(
          level === "error" ? "console-error" : "console-log",
          { elementInfo: msg, level }
        );
      };

    const origLog = console.log,
      origWarn = console.warn,
      origError = console.error,
      origInfo = console.info,
      origDebug = console.debug;
    console.log = interceptConsole("log", origLog);
    console.warn = interceptConsole("warn", origWarn);
    console.error = interceptConsole("error", origError);
    console.info = interceptConsole("info", origInfo);
    console.debug = interceptConsole("debug", origDebug);

    // JS error tracking
    let errorCount = 0;
    const MAX_ERRORS = 50;

    const handleError = (event: ErrorEvent) => {
      if (errorCount >= MAX_ERRORS) return;
      errorCount++;
      let errorInfo = String(event.message || "Unknown error").slice(0, 150);
      if (event.filename)
        errorInfo += ` (at ${event.filename.split("/").pop()}:${event.lineno})`;
      sendToInspector("error", { elementInfo: errorInfo, level: "error" });
    };

    const handleRejection = (event: PromiseRejectionEvent) => {
      if (errorCount >= MAX_ERRORS) return;
      errorCount++;
      const reason =
        event.reason?.message || event.reason?.toString() || "Promise rejected";
      sendToInspector("error", {
        elementInfo: String(reason).slice(0, 150),
        level: "error",
      });
    };

    window.addEventListener("error", handleError);
    window.addEventListener("unhandledrejection", handleRejection);

    // MutationObserver + periodic scan - detect error overlays
    const __attachedOverlays = new WeakSet<Element>();
    const isOverlay = (node: Element): boolean => {
      try {
        const s = window.getComputedStyle(node);
        const z = parseInt(s.zIndex) || 0;
        const htmlNode = node as HTMLElement;
        return (
          (s.position === "fixed" || s.position === "absolute") &&
          (z > 1000 ||
            (htmlNode.offsetWidth > window.innerWidth * 0.8 &&
              htmlNode.offsetHeight > window.innerHeight * 0.5))
        );
      } catch (_e) {
        return false;
      }
    };
    const attachOverlay = (node: Element) => {
      if (__attachedOverlays.has(node)) return;
      __attachedOverlays.add(node);
      sendToInspector("error-overlay", {
        elementInfo:
          "\u0644\u0627\u06CC\u0647 \u062E\u0637\u0627: " +
          (node.textContent || "").slice(0, 200),
        level: "error",
      });
      node.addEventListener(
        "click",
        (e: Event) => {
          const me = e as MouseEvent;
          sendToInspector("click", {
            elementInfo: getElementInfo(me.target) + " (overlay)",
            position: getPositionPercent(me),
          });
        },
        true
      );
      node.addEventListener(
        "pointerdown",
        (e: Event) => {
          const pe = e as PointerEvent;
          sendToInspector("click", {
            elementInfo: getElementInfo(pe.target) + " (overlay pointerdown)",
            position: getPositionPercent(pe),
          });
        },
        true
      );
      if ((node as HTMLElement).shadowRoot) {
        (node as HTMLElement).shadowRoot!.addEventListener(
          "click",
          (e: Event) => {
            sendToInspector("click", {
              elementInfo: getElementInfo(e.target) + " (shadow)",
              position: { xPercent: 50, yPercent: 50 },
            });
          },
          true
        );
      }
    };

    let overlayObs: MutationObserver | undefined;
    try {
      overlayObs = new MutationObserver((mutations) => {
        mutations.forEach((m) =>
          m.addedNodes.forEach((node) => {
            if (node.nodeType !== 1) return;
            if (isOverlay(node as Element)) attachOverlay(node as Element);
          })
        );
      });
      if (document.body)
        overlayObs.observe(document.body, { childList: true, subtree: true });
      else
        document.addEventListener("DOMContentLoaded", () =>
          overlayObs?.observe(document.body, {
            childList: true,
            subtree: true,
          })
        );
    } catch (_e) {
      // MutationObserver not available
    }

    // Periodic scan
    const overlayScan = setInterval(() => {
      try {
        document
          .querySelectorAll(
            '[style*="position: fixed"], [style*="position:fixed"], nextjs-portal, [id*="overlay"], [id*="error"], [class*="overlay"]'
          )
          .forEach((el) => {
            if (isOverlay(el)) attachOverlay(el);
            if ((el as HTMLElement).shadowRoot && !__attachedOverlays.has(el))
              attachOverlay(el);
          });
      } catch (_e) {
        // scan failed
      }
    }, 2000);

    connectWS();
    const heartbeat = setInterval(() => {
      if (ws && wsReady)
        try {
          ws.send(JSON.stringify({ type: "ping" }));
        } catch (_e) {
          // send failed
        }
    }, 25000);

    // Respond to URL requests from parent (request-response pattern)
    const _handleUrlRequest = (event: MessageEvent) => {
      if (event.data?.type === "inspector-get-url") {
        if (isInIframe) {
          try {
            window.parent.postMessage(
              {
                type: "inspector-current-url",
                pageUrl: window.location.href,
                title: document.title,
                timestamp: Date.now(),
              },
              "*"
            );
          } catch (_e) {
            // cross-origin
          }
        }
      }
    };
    window.addEventListener("message", _handleUrlRequest);

    // Fallback postMessage
    if (isInIframe) {
      try {
        window.parent.postMessage(
          {
            type: "inspector-bridge-ready",
            pageUrl: window.location.href,
          },
          "*"
        );
      } catch (_e) {
        // cross-origin
      }
    }

    return () => {
      window.removeEventListener("click", handleClick, true);
      window.removeEventListener("pointerdown", handlePointerDown, true);
      window.removeEventListener("input", handleInput, true);
      window.removeEventListener("scroll", handleScroll, true);
      window.removeEventListener("focus", handleFocus, true);
      window.removeEventListener("error", handleError);
      window.removeEventListener("unhandledrejection", handleRejection);
      window.removeEventListener("popstate", _notifyUrlChange);
      window.removeEventListener("hashchange", _notifyUrlChange);
      clearInterval(_urlCheckInterval);
      history.pushState = _origPushState;
      history.replaceState = _origReplaceState;
      window.removeEventListener("message", _handleUrlRequest);
      console.log = origLog;
      console.warn = origWarn;
      console.error = origError;
      console.info = origInfo;
      console.debug = origDebug;
      if (overlayObs) overlayObs.disconnect();
      clearInterval(heartbeat);
      clearInterval(overlayScan);
      if (ws) {
        try {
          ws.close();
        } catch (_e) {
          // close failed
        }
      }
    };
  }, []);

  return null;
}
