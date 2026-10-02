import { post } from "./api.js";
import { toast } from "./ui.js";
import { watchJob } from "./jobwindow.js";

let onJobDone = () => {};
export function setOnJobDone(fn) { onJobDone = fn; }

let busy = false;

export async function runAction(kind, payload, title) {
  if (busy) {
    toast("Ya hay una tarea en curso", "info");
    return;
  }
  busy = true;
  try {
    const { job_id } = await post(`/api/actions/${kind}`, payload);
    watchJob(job_id, title, (ok) => {
      busy = false;
      toast(ok ? `${title}: completado` : `${title}: error`, ok ? "ok" : "err");
      onJobDone(ok);
    });
  } catch (e) {
    busy = false;
    toast(`No se pudo iniciar: ${e.message}`, "err");
  }
}
