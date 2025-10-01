# Agent Last Response
**Timestamp:** 2025-10-01 04:36  
**Source:** agent_chat:planner  
**Query:** Reverse geocoding popup

## Response
Quick diagnosis — probable causes (fast checklist)
- Network/auth: /v1/reverse request failing (401/403/429/500) and hook swallowing the error → popup shows empty string. Check DevTools Network for status and response body.
- Coordinate ordering: MapLibre gives (lng, lat) but gateway expects lat, lon. If you reversed them, reverse returns nothing or a different place. Verify query uses lat=...,lon=...
- Response shape mismatch: gateway returns an object {display_name: ...} but hook expects an array (or vice‑versa). That can lead to undefined display_name.
- Debounce/Abort race: aborting the in-flight request then trying to render result may clear the popup content.
- CORS/preflight: request blocked — check console for CORS errors.
- Sanitization/rendering bug: escapeHtml or innerHTML use might be removing the content inadvertently.
- Silent failure in fetch wrapper: fetchWithApiKey may be catching errors and returning {} or null.

Immediate debug steps (do these first)
1. Click map while open DevTools → Network tab. Inspect the /v1/reverse request:
   - Status code (200 vs 4xx/5xx).
   - Response body (is display_name present? array or object?).
   - Response headers: X-Request-ID present?
2. Check Console for CORS or JS exceptions.
3. Verify request query string ordering: lat=...&lon=... (not reversed).
4. If auth enabled, confirm X-API-Key header sent (or gateway has PUBLIC_PATHS including /v1/reverse).
5. Confirm the hook's return values (console.log the parse result inside the hook if needed).

Concrete plan to fix and harden (summary)
- Make fetchWithApiKey robust: surface non-2xx errors with body and headers, include X-Request-ID, timeouts, and clear error propagation.
- Ensure useReverseGeocode validates and normalizes coords (lat, lon), handles both response shapes (array/object), returns explicit states (loading, error, result) and requestId, and doesn't swallow errors.
- Update ReverseGeocodePopup to show loading/error/fallback text instead of blank, and render safely (no innerHTML).
- In MapWithReverse, explicitly extract lng/lat from the map event and call the hook with lat, lon.
- Add small unit tests for parsing and an integration smoke test (mock fetch) and add a temporary in‑UI error banner when reverse fails.
- Add instrumentation: console debug lines and capture requestId to help correlate backend logs.

Files to create/update (JSON + code for critical functions below)
```json
{
  "files_to_create": [
    "frontend/src/utils/fetchWithApiKey.ts",
    "frontend/src/hooks/useReverseGeocode.ts",
    "frontend/src/components/ReverseGeocodePopup.tsx"
  ],
  "files_to_update": [
    "frontend/src/components/MapWithReverse.tsx",
    "frontend/src/App.tsx",
    "frontend/README.md",
    "docker-compose.yml"
  ],
  "summary": "Fix empty-address popup by making the fetch wrapper and reverse-hook robust (clear errors, timeout, parse multiple response shapes), ensure correct lat/lon ordering from MapLibre, add explicit loading/error UI in the popup, and add tests + debug hooks to surface request_id and backend errors to the developer.",
  "steps": [
    "Reproduce the issue and inspect /v1/reverse in browser DevTools (network/status/body/headers).",
    "Create/update fetchWithApiKey.ts to return structured errors + include headers and request id.",
    "Implement useReverseGeocode.ts: validate coords, normalize (lat,lon), debounce + AbortController, parse both array/object responses, return { result, loading, error, requestId }.",
    "Update ReverseGeocodePopup.tsx to show 'Loading…', 'No address found', and error messages; ensure safe rendering (no innerHTML).",
    "Update MapWithReverse.tsx to pass lat, lon (not lng,lat) and to show requestId in console for correlation.",
    "Add unit tests for useReverseGeocode parser logic and MapWithReverse coordinate passing (mocks), and a manual test plan entry in README.",
    "Deploy locally and run manual test: click map → inspect network + popup shows address or error. Correlate X-Request-ID with gateway logs.",
    "If 4xx/5xx or CORS: update gateway PUBLIC_PATHS or VITE_API_KEY and ensure gateway CORS allows frontend origin; re-run tests.",
    "If rate limiting observed: add client-side debounce increase and short-term cache; coordinate server-side rate limit tuning (in-memory → redis if needed)."
  ],
  "risks": [
    "Exposing VITE_API_KEY in browser if used for local dev; must document and avoid for prod.",
    "Client-side fixes hide server-side issues (e.g., outage, high latency) — must still surface requestId and error codes for ops.",
    "Incorrect silent catches may make debugging harder; ensure we log and surface errors in UI during dev.",
    "Adding retries without backoff may worsen backend load if rate-limited; avoid automatic hammering."
  ]
}
```

Critical code updates (exact file paths)

1) frontend/src/utils/fetchWithApiKey.ts
- Purpose: robust fetch wrapper that injects X-API-Key when available, sets timeout, parses non-2xx errors, and exposes headers (X-Request-ID) and raw body for debugging.

File: frontend/src/utils/fetchWithApiKey.ts
```ts
// frontend/src/utils/fetchWithApiKey.ts
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8001';
const API_KEY = import.meta.env.VITE_API_KEY || undefined;
const DEFAULT_TIMEOUT_MS = 8000;

type FetchResult = {
  ok: boolean;
  status: number;
  json?: any;
  text?: string;
  headers: Headers;
};

export async function fetchWithApiKey(path: string, opts: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<FetchResult> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const headers = new Headers(opts.headers || {});
    headers.set('Accept', 'application/json');
    if (API_KEY) {
      headers.set('X-API-Key', API_KEY);
    }

    const res = await fetch(`${API_BASE}${path}`, { ...opts, headers, signal: controller.signal });

    const result: FetchResult = {
      ok: res.ok,
      status: res.status,
      headers: res.headers,
    };

    // Try parse json, fallback to text
    try {
      result.json = await res.clone().json();
    } catch (e) {
      try {
        result.text = await res.text();
      } catch {
        result.text = undefined;
      }
    }

    if (!res.ok) {
      // include body/text for debugging; caller handles errors
      throw {
        message: `HTTP ${res.status}`,
        status: res.status,
        json: result.json,
        text: result.text,
        headers: res.headers,
      };
    }

    return result;
  } catch (err) {
    if ((err as any).name === 'AbortError') {
      throw { message: 'Request timed out', name: 'TimeoutError' };
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}
export default fetchWithApiKey;
```

2) frontend/src/hooks/useReverseGeocode.ts
- Purpose: expose execute(lat, lon) with debounce + AbortController; robust parsing of response shapes and returns structured result including requestId.

File: frontend/src/hooks/useReverseGeocode.ts
```ts
// frontend/src/hooks/useReverseGeocode.ts
import { useState, useRef, useCallback } from 'react';
import fetchWithApiKey from '../utils/fetchWithApiKey';

type ReverseResult = {
  display_name?: string;
  lat?: string;
  lon?: string;
  raw?: any;
  requestId?: string | null;
};

export default function useReverseGeocode(debounceMs = 200) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReverseResult | null>(null);
  const lastRequestId = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimer = useRef<number | null>(null);

  const normalizeCoords = (lat: number, lon: number) => {
    // quick validation: lat [-90,90], lon [-180,180]
    if (!isFinite(lat) || !isFinite(lon)) return null;
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
    return { lat, lon };
  };

  const parseResponse = (jsonOrObj: any): ReverseResult => {
    // Gateway might return object {display_name,...} or array [ {display_name,...}, ... ]
    if (!jsonOrObj) return { raw: jsonOrObj };
    if (Array.isArray(jsonOrObj)) {
      const first = jsonOrObj[0] || null;
      if (first) {
        return {
          display_name: first.display_name,
          lat: first.lat,
          lon: first.lon,
          raw: jsonOrObj,
        };
      }
      return { raw: jsonOrObj };
    }
    // object case
    if (typeof jsonOrObj === 'object') {
      return {
        display_name: jsonOrObj.display_name,
        lat: jsonOrObj.lat,
        lon: jsonOrObj.lon,
        raw: jsonOrObj,
      };
    }
    return { raw: jsonOrObj };
  };

  const execute = useCallback(async (latIn: number, lonIn: number) => {
    setError(null);
    setResult(null);

    const coords = normalizeCoords(latIn, lonIn);
    if (!coords) {
      setError('Invalid coordinates');
      return { ok: false, error: 'invalid_coordinates' };
    }

    // debounce
    if (debounceTimer.current) {
      window.clearTimeout(debounceTimer.current);
    }

    return new Promise(async (resolve) => {
      debounceTimer.current = window.setTimeout(async () => {
        setLoading(true);
        // abort any previous
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
        }
        const localController = new AbortController();
        abortControllerRef.current = localController;
        try {
          // Important: use lat, lon ordering in querystring
          const qs = `?lat=${encodeURIComponent(coords.lat)}&lon=${encodeURIComponent(coords.lon)}`;
          const path = `/v1/reverse${qs}`;
          const res = await fetchWithApiKey(path, { signal: localController.signal });
          // extract x-request-id if present
          const requestId = res.headers.get('x-request-id') || (res.json && res.json.request_id) || null;
          lastRequestId.current = requestId;

          const parsed = parseResponse(res.json ?? res.text);
          parsed.requestId = requestId || null;
          setResult(parsed);
          setLoading(false);
          resolve({ ok: true, result: parsed });
        } catch (err: any) {
          setLoading(false);
          // err may be structured from fetchWithApiKey
          const msg = err?.message || 'Unknown error';
          // include status if present
          if (err?.status) {
            setError(`${msg} (status ${err.status})`);
          } else {
            setError(msg);
          }
          // surface requestId if present
          try {
            const headers = err?.headers;
            const requestId = headers?.get ? headers.get('x-request-id') : null;
            lastRequestId.current = requestId || null;
          } catch {}
          resolve({ ok: false, error: err, requestId: lastRequestId.current || null });
        }
      }, debounceMs);
    });
  }, [debounceMs]);

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    if (debounceTimer.current) {
      window.clearTimeout(debounceTimer.current);
      debounceTimer.current = null;
    }
    setLoading(false);
  }, []);

  return {
    execute,
    cancel,
    loading,
    error,
    result,
    lastRequestId: lastRequestId.current,
  };
}
```

3) frontend/src/components/ReverseGeocodePopup.tsx
- Purpose: display loading / address / no result / error, safe rendering.

File: frontend/src/components/ReverseGeocodePopup.tsx
```tsx
// frontend/src/components/ReverseGeocodePopup.tsx
import React from 'react';

type Props = {
  lat: number;
  lon: number;
  loading: boolean;
  displayName?: string | undefined | null;
  error?: string | null;
  requestId?: string | null;
};

export default function ReverseGeocodePopup({ lat, lon, loading, displayName, error, requestId }: Props) {
  return (
    <div className="reverse-popup" style={{ minWidth: 220 }}>
      <div style={{ fontSize: 12, color: '#666' }}>
        {lat.toFixed(5)}, {lon.toFixed(5)}
        {requestId ? <div style={{ fontSize: 10, marginTop: 4 }}>req: {requestId}</div> : null}
      </div>
      <div style={{ marginTop: 6 }}>
        {loading && <div>Loading address…</div>}
        {!loading && error && <div style={{ color: 'crimson' }}>Error: {error}</div>}
        {!loading && !error && !displayName && <div style={{ color: '#666' }}>No address found</div>}
        {!loading && displayName && <div style={{ fontWeight: 600 }}>{displayName}</div>}
      </div>
    </div>
  );
}
```

4) Update MapWithReverse to pass lat, lon
- Ensure MapLibre event extraction uses event.lngLat.lng / event.lngLat.lat and calls execute(lat, lon).

File to update: frontend/src/components/MapWithReverse.tsx
```tsx
// frontend/src/components/MapWithReverse.tsx
import React, { useState, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import useReverseGeocode from '../hooks/useReverseGeocode';
import ReverseGeocodePopup from './ReverseGeocodePopup';

export default function MapWithReverse() {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const [popupState, setPopupState] = useState<{
    lat: number;
    lon: number;
    loading: boolean;
    displayName?: string | null;
    error?: string | null;
    requestId?: string | null;
  } | null>(null);

  const { execute, loading, result, error, lastRequestId, cancel } = useReverseGeocode(200);

  const initMap = (el: HTMLDivElement) => {
    if (mapContainerRef.current) return;
    mapContainerRef.current = el;
    const map = new maplibregl.Map({
      container: el,
      style: 'https://demotileserver/style.json',
      center: [77.5946, 12.9716],
      zoom: 10,
    });

    map.on('click', async (e: any) => {
      // maplibre event: e.lngLat.lng, e.lngLat.lat
      const lng = e.lngLat.lng;
      const lat = e.lngLat.lat;
      // show initial popup state
      setPopupState({ lat, lon: lng, loading: true });
      try {
        const r = await execute(lat, lng);
        // `execute` resolves with {ok, result} or {ok:false, error}
        if ((r as any).ok) {
          const res = (r as any).result;
          setPopupState({
            lat,
            lon: lng,
            loading: false,
            displayName: res?.display_name || null,
            requestId: res?.requestId || null,
          });
          console.debug('reverse reqId=', res?.requestId);
        } else {
          setPopupState({
            lat,
            lon: lng,
            loading: false,
            error: (r as any).error?.message || 'Reverse failed',
            requestId: (r as any).requestId || null,
          });
        }
      } catch (ex) {
        setPopupState({ lat, lon: lng, loading: false, error: (ex as any).message || 'Unknown', requestId: null });
      }
    });
  };

  return (
    <div style={{ position: 'relative', height: '100%' }}>
      <div ref={initMap as any} style={{ height: '100%' }} />
      {popupState ? (
        <div className="map-popup" style={{ position: 'absolute', left: 10, top: 10 }}>
          <ReverseGeocodePopup
            lat={popupState.lat}
            lon={popupState.lon}
            loading={popupState.loading}
            displayName={popupState.displayName}
            error={popupState.error}
            requestId={popupState.requestId}
          />
        </div>
      ) : null}
    </div>
  );
}
```

Notes & follow-ups
- If after these changes the Network shows 401/403, update gateway PUBLIC_PATHS to include /v1/reverse for local dev or provide VITE_API_KEY in .env with a short-lived dev key.
- If you see 429s, increase client debounce (e.g., 500ms) and consider small client cache for repeated clicks in a small radius.
- Add a small debug toggle in UI to show raw response and X-Request-ID to ease correlating logs (dev-only).
- Add unit tests: mock fetchWithApiKey response shapes (array/object), ensure parseResponse returns display_name. Add integration test to assert MapWithReverse calls execute with lat (not lng) as first param.

If you want, I can:
- Prepare the PR with the above patches (diffs for the listed files + tests).
- Add a short e2e Playwright test that hits the running gateway and asserts the popup shows a non-empty address for known coords (requires gateway to allow unauth or configured test key).
