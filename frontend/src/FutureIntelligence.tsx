import { useEffect, useState } from "react";
import { Bell, Brain, CalendarClock, Cpu, Globe2, ShieldAlert, Sparkles } from "lucide-react";

const API = String(import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

type Props = { machineId?: string; language: "en" | "hi" | "hinglish"; question?: string; assessment?: any };

const copy = {
  en: { title: "NEXT-GEN INDUSTRIAL INTELLIGENCE", sub: "Anomaly detection, alerts, digital twin, edge readiness & maintenance workflow", anomaly: "Anomaly Detection", alerts: "Smart Alerts", twin: "Digital Twin", edge: "Edge AI Ready", schedule: "Maintenance Scheduling", feedback: "Technician Feedback", scheduleBtn: "Plan Maintenance", feedbackBtn: "Save Feedback", feedbackPlaceholder: "Was this AI recommendation useful?", noAnomaly: "No significant anomaly detected", baseline: "Baseline building", save: "Saved", simulate: "Run What-If Simulation", simulation: "Simulation Result" },
  hi: { title: "नेक्स्ट-जेन इंडस्ट्रियल इंटेलिजेंस", sub: "Anomaly detection, alerts, digital twin, edge readiness और maintenance workflow", anomaly: "एनोमली डिटेक्शन", alerts: "स्मार्ट अलर्ट", twin: "डिजिटल ट्विन", edge: "एज AI तैयार", schedule: "मेंटेनेंस शेड्यूल", feedback: "टेक्नीशियन फीडबैक", scheduleBtn: "मेंटेनेंस प्लान करें", feedbackBtn: "फीडबैक सेव करें", feedbackPlaceholder: "क्या AI recommendation उपयोगी थी?", noAnomaly: "कोई महत्वपूर्ण anomaly नहीं मिली", baseline: "Baseline बन रहा है", save: "सेव", simulate: "What-If Simulation चलाएँ", simulation: "Simulation Result" },
  hinglish: { title: "NEXT-GEN INDUSTRIAL INTELLIGENCE", sub: "Anomaly detection, alerts, digital twin, edge readiness aur maintenance workflow", anomaly: "Anomaly Detection", alerts: "Smart Alerts", twin: "Digital Twin", edge: "Edge AI Ready", schedule: "Maintenance Scheduling", feedback: "Technician Feedback", scheduleBtn: "Maintenance Plan Karo", feedbackBtn: "Feedback Save Karo", feedbackPlaceholder: "Kya AI recommendation useful thi?", noAnomaly: "Koi significant anomaly detect nahi hui", baseline: "Baseline build ho raha hai", save: "Save", simulate: "What-If Simulation Chalao", simulation: "Simulation Result" },
} as const;

export default function FutureIntelligence({ machineId, language, question = "", assessment }: Props) {
  const t = copy[language];
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [twin, setTwin] = useState<any[]>([]);
  const [edge, setEdge] = useState<any>(null);
  const [rul, setRul] = useState<any>(null);
  const [models, setModels] = useState<any>(null);
  const [feedback, setFeedback] = useState("");
  const [saved, setSaved] = useState("");
  const [priority, setPriority] = useState("MEDIUM");
  const [date, setDate] = useState("");
  const [action, setAction] = useState("Maintenance inspection");
  const [sim, setSim] = useState({ air_temperature: "", process_temperature: "", rotational_speed: "", torque: "", tool_wear: "" });
  const [simResult, setSimResult] = useState<any>(null);
  const [simulating, setSimulating] = useState(false);

  useEffect(() => {
    if (!machineId) return;
    const load = async () => {
      try {
        const [a, b, c, d, e, f] = await Promise.all([
          fetch(API + "/future/anomalies/" + encodeURIComponent(machineId) + "?limit=100"),
          fetch(API + "/future/alerts"),
          fetch(API + "/future/digital-twin"),
          fetch(API + "/future/edge/status"),
          fetch(API + "/future/rul/live/" + encodeURIComponent(machineId)),
          fetch(API + "/future/model-registry"),
        ]);
        if (a.ok) setAnomalies((await a.json()).anomalies || []);
        if (b.ok) setAlerts((await b.json()).alerts || []);
        if (c.ok) setTwin((await c.json()).machines || []);
        if (d.ok) setEdge(await d.json());
        if (e.ok) setRul(await e.json());
        if (f.ok) setModels(await f.json());
      } catch {}
    };
    load();
  }, [machineId]);

  useEffect(() => {
    const m = twin.find(x => x.machine_id === machineId);
    if (!m) return;
    setSim({
      air_temperature: m.air_temperature == null ? "" : String(m.air_temperature),
      process_temperature: m.process_temperature == null ? "" : String(m.process_temperature),
      rotational_speed: m.rotational_speed == null ? "" : String(m.rotational_speed),
      torque: m.torque == null ? "" : String(m.torque),
      tool_wear: m.tool_wear == null ? "" : String(m.tool_wear),
    });
  }, [machineId, twin]);

  const saveFeedback = async () => {
    if (!machineId || !feedback.trim()) return;
    try {
      const r = await fetch(API + "/future/feedback", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ machine_id: machineId, feedback, question, assessment_risk: assessment?.overall_risk || "UNKNOWN" })
      });
      if (r.ok) { setSaved(t.save); setFeedback(""); }
    } catch {}
  };

  const schedule = async () => {
    if (!machineId || !date) return;
    try {
      const r = await fetch(API + "/future/schedule", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ machine_id: machineId, priority, action, scheduled_for: new Date(date).toISOString() })
      });
      if (r.ok) setSaved(t.scheduleBtn);
    } catch {}
  };

  const simulate = async () => {
    if (!machineId) return;
    setSimulating(true);
    setSimResult(null);
    try {
      const payload: Record<string, unknown> = { machine_id: machineId };
      Object.entries(sim).forEach(([key, value]) => {
        if (value.trim() !== "") payload[key] = Number(value);
      });
      const params = new URLSearchParams({ machine_id: machineId });
      Object.entries(payload).forEach(([key, value]) => {
        if (key !== "machine_id" && value !== undefined) params.set(key, String(value));
      });
      const r = await fetch(API + "/future/digital-twin/simulate?" + params.toString(), {
        method: "GET",
        headers: { "Accept": "application/json" }
      });
      const data = await r.json().catch(() => ({}));
      if (r.ok) setSimResult(data);
      else setSimResult({ error: data.detail || "Simulation failed (HTTP " + r.status + ")" });
    } catch {
      setSimResult({ error: "Unable to reach simulation API" });
    } finally {
      setSimulating(false);
    }
  };

  const twinMachine = twin.find(x => x.machine_id === machineId);
  const updateSim = (key: keyof typeof sim, value: string) => setSim(prev => ({ ...prev, [key]: value }));

  return <section className="panel" style={{marginTop:24}}>
    <div className="head">
      <div><small><Sparkles size={14}/> {t.title}</small><h2>{t.sub}</h2></div>
      <span className="system-status"><Globe2 size={14}/> {language.toUpperCase()}</span>
    </div>
    <div className="grid lower">
      <div className="panel"><small><ShieldAlert size={14}/> {t.anomaly}</small><h3>{anomalies.length} event(s)</h3>
        {anomalies.length ? anomalies.map((a:any,i:number)=><div className="status" key={i}><b>{a.sensor} · {a.severity}</b><span>z-score {a.z_score}</span></div>) : <div className="status"><b>{t.noAnomaly}</b><span>{t.baseline}</span></div>}
      </div>
      <div className="panel"><small><Bell size={14}/> {t.alerts}</small><h3>{alerts.length} active</h3>
        {alerts.slice(0,3).map((a:any)=><div className="status" key={a.machine_id}><b>{a.machine_id} · {a.priority}</b><span>{a.recommended_action}</span></div>)}
      </div>
      <div className="panel"><small><Brain size={14}/> {t.twin}</small><h3>{twinMachine?.machine_id || "--"} · {twinMachine?.risk_level || "--"}</h3>
        <div className="status"><b>Failure risk</b><span>{twinMachine ? (Number(twinMachine.failure_probability)*100).toFixed(2)+"%" : "--"}</span></div>
        <div className="status"><b>RPM / Torque</b><span>{twinMachine?.rotational_speed ?? "--"} / {twinMachine?.torque ?? "--"}</span></div>
      </div>
      <div className="panel"><small><Cpu size={14}/> {t.edge}</small><h3>{edge?.edge_ready ? "READY" : "CHECK"}</h3>
        <div className="status"><b>Current mode</b><span>{edge?.mode || "cloud"}</span></div><div className="status"><b>Edge contract</b><span>{edge?.inference_contract || "--"}</span></div>
      </div>
    </div>
    <div className="grid lower">
      <div className="panel"><small>RUL & MODEL GOVERNANCE</small><h3>{rul?.available ? (Number(rul.predicted_rul_cycles).toFixed(1) + " cycles") : "Live RUL waiting for 21 sensors"}</h3><div className="status"><b>Champion</b><span>{models?.active?.failure || "rf-industrial-v1"}</span></div><div className="status"><b>Challengers</b><span>{(models?.candidate_models || []).join(", ")}</span></div></div>
      <div className="panel"><small><CalendarClock size={14}/> {t.schedule}</small>
        <div className="copilot-input"><select value={priority} onChange={e=>setPriority(e.target.value)}><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>CRITICAL</option></select><input value={action} onChange={e=>setAction(e.target.value)} placeholder="Action"/><input type="datetime-local" value={date} onChange={e=>setDate(e.target.value)}/><button type="button" onClick={schedule}>{t.scheduleBtn}</button></div>
      </div>
      <div className="panel"><small><Brain size={14}/> {t.feedback}</small>
        <div className="copilot-input"><input value={feedback} onChange={e=>setFeedback(e.target.value)} placeholder={t.feedbackPlaceholder}/><button type="button" onClick={saveFeedback}>{t.feedbackBtn}</button></div>
        {saved && <div className="status"><b>{saved}</b></div>}
      </div>
    </div>
    <div className="panel" style={{marginTop:16}}>
      <small><Brain size={14}/> {t.twin} · {t.simulation}</small>
      <h3>{t.simulation}</h3>
      <div className="copilot-input" style={{display:"grid",gridTemplateColumns:"repeat(5,minmax(0,1fr))",gap:8}}>
        <input type="number" step="any" value={sim.air_temperature} onChange={e=>updateSim("air_temperature",e.target.value)} placeholder="Air °C"/>
        <input type="number" step="any" value={sim.process_temperature} onChange={e=>updateSim("process_temperature",e.target.value)} placeholder="Process °C"/>
        <input type="number" step="any" value={sim.rotational_speed} onChange={e=>updateSim("rotational_speed",e.target.value)} placeholder="RPM"/>
        <input type="number" step="any" value={sim.torque} onChange={e=>updateSim("torque",e.target.value)} placeholder="Torque"/>
        <input type="number" step="any" value={sim.tool_wear} onChange={e=>updateSim("tool_wear",e.target.value)} placeholder="Tool wear"/>
      </div>
      <div className="copilot-input" style={{marginTop:8}}>
        <button type="button" onClick={simulate} disabled={simulating || !machineId}>{simulating ? "Running..." : t.simulate}</button>
      </div>
      {simResult && <div className="status" style={{marginTop:8}}>
        <b>{simResult.error ? "Simulation error" : (simResult.predicted_result?.prediction || simResult.predicted_result?.risk_level || "Simulation complete")}</b>
        <span>{simResult.error || ("Failure probability: " + (simResult.predicted_result?.failure_probability != null ? (Number(simResult.predicted_result.failure_probability)*100).toFixed(2)+"%" : "--"))}</span>
      </div>}
    </div>
  </section>;
}