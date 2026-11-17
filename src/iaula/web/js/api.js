async function req(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).error || msg; } catch { /* keep */ }
    throw new Error(msg);
  }
  return res.json();
}

async function raw(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).error || msg; } catch { /* keep */ }
    throw new Error(msg);
  }
  return res;
}

export const get = (p) => req(p);
export const post = (p, body) => req(p, { method: "POST", body: JSON.stringify(body || {}) });
export const postBlob = (p, body) =>
  raw(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
export const postAudio = (p, blob) =>
  raw(p, { method: "POST", headers: { "Content-Type": blob.type || "application/octet-stream" }, body: blob });
export const jobStatus = (id) => get(`/api/jobs/${id}`);
