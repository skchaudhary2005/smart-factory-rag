import MachineMonitoring from "./MachineMonitoring";
import SensorIntelligence from "./SensorIntelligence";
import { lazy, Suspense, useEffect, useState } from 'react';
import { Activity, Cpu, Gauge, RefreshCw, ShieldCheck, Thermometer, Wrench, Radio, BrainCircuit, Network, Factory, ChevronDown } from "lucide-react";
import "./App.css";
import "./CommandCenterPrototype.css";
const Analytics = lazy(() => import('./Analytics'));
const TelemetryChart = lazy(() => import('./TelemetryChart'));
import FactoryArchitecture from "./FactoryArchitecture";
import Factory3D from "./Factory3D";
import FutureIntelligence from "./FutureIntelligence";

const API=String(import.meta.env.VITE_API_BASE_URL||"http://localhost:8000").replace(/\/$/,"");
type Language = "auto" | "en" | "hi" | "hinglish";

export default function App(){
 const [summary,setSummary]=useState<any>(null);
 const [machines,setMachines]=useState<any[]>([]);
 const [selectedMachineId,setSelectedMachineId]=useState<string>("");
 const [history,setHistory]=useState<any[]>([]);
 const [error,setError]=useState("");
 const load=async()=>{
  try{
   setError("");
   const [a,b]=await Promise.all([fetch(`${API}/analytics/summary`),fetch(`${API}/analytics/machines`)]);
   if(!a.ok||!b.ok)throw Error("Backend API unavailable");
   const s=await a.json(),m=await b.json();
   setSummary(s);
   const liveMachines=(m.machines||[]).filter((x:any)=>String(x.machine_id).toLowerCase()!=="derived");
   setMachines(liveMachines);
   const preferred=liveMachines.find((x:any)=>x.machine_id===selectedMachineId)||liveMachines.find((x:any)=>x.machine_id==="M-001")||liveMachines[0];
   if(preferred){
    setSelectedMachineId(preferred.machine_id);
    try{
     const h=await fetch(`${API}/analytics/machines/${encodeURIComponent(preferred.machine_id)}/history?limit=50`);
     if(h.ok){
      const x=await h.json();
      setHistory((x.history||[]).reverse());
     }
    }catch{
     setHistory([]);
    }
   }else{
    setSelectedMachineId("");
    setHistory([]);
   }
  }catch(e){setError(e instanceof Error?e.message:"Connection error")}
 };
 useEffect(()=>{load();const t=setInterval(load,5000);return()=>clearInterval(t)},[selectedMachineId]);
 const machine=machines.find((x:any)=>x.machine_id===selectedMachineId)||machines[0];
 const latest=history[history.length-1];
 const [assessment,setAssessment]=useState<any>(null); const [question,setQuestion]=useState("What maintenance checks should be performed for this machine?"); const [ragAnswer,setRagAnswer]=useState<any>(null);

 const [assessing,setAssessing]=useState(false);
 const [language,setLanguage]=useState<Language>("auto");

 const runAssessment=async()=>{
  try{
   setAssessing(true);
   setError("");

   const payload={
    machine_type:latest?.machine_type||"L",
    air_temperature:latest?.air_temperature??298.3,
    process_temperature:latest?.process_temperature??307.2,
    rotational_speed:latest?.rotational_speed??1440,
    torque:latest?.torque??39.5,
    tool_wear:latest?.tool_wear??10,
    op_setting_1:0,
    op_setting_2:0,
    op_setting_3:0,
    sensors:Array(21).fill(0),
    question,
    language: language === "auto" ? undefined : language
   };

   // Run the industrial assessment FIRST. RAG is optional enrichment and
   // must never delay or block the actual assessment result.
   const response=await fetch(
    `${API}/industrial/maintenance-assessment`,
    {
     method:"POST",
     headers:{"Content-Type":"application/json"},
     body:JSON.stringify(payload),
    }
   );

   if(!response.ok){
    let detail="";
    try{ detail=await response.text(); }catch{}
    throw Error(`Maintenance assessment failed (${response.status})${detail?`: ${detail.slice(0,180)}`:""}`);
   }

   const assessmentResult=await response.json();
   setAssessment(assessmentResult);

   // RAG is optional enrichment. Give it a short timeout so a slow RAG
   // service can never prevent the assessment UI from showing a result.
   try{
    const controller=new AbortController();
    const timer=window.setTimeout(()=>controller.abort(),5000);
    const ragResponse=await fetch(`${API}/query`,{
     method:"POST",
     headers:{"Content-Type":"application/json"},
     body:JSON.stringify({question,top_k:3,rerank:false,language:language === "auto" ? undefined : language}),
     signal:controller.signal,
    });
    window.clearTimeout(timer);
    if(ragResponse.ok){
     setRagAnswer(await ragResponse.json());
    }else{
     setRagAnswer(null);
    }
   }catch{
    setRagAnswer(null);
   }
  }catch(e){
   setError(e instanceof Error?e.message:"Maintenance assessment failed");
  }finally{
   setAssessing(false);
  }
 };

 return <div className="app command-app">
  <div className="ambient-grid" aria-hidden="true"></div>
  <header className="command-header">
   <div className="brand-block">
    <div className="brand-mark"><Factory size={18}/></div>
    <div><div className="eyebrow">INDUSTRIAL AI PLATFORM · LIVE</div><h1>Smart Factory RAG</h1><p>Predictive maintenance · machine intelligence · industrial copilot</p></div>
   </div>
   <nav className="command-nav" aria-label="Smart Factory sections">
    <a href="#overview"><span>01</span>Overview</a><a href="#machine"><span>02</span>Machine</a><a href="#telemetry"><span>03</span>Telemetry</a><a href="#copilot"><span>04</span>AI Copilot</a><a href="#alerts"><span>05</span>Alerts</a><a href="#analytics"><span>06</span>Analytics</a><a href="#maintenance"><span>07</span>Maintenance</a><a href="#intelligence"><span>08</span>Future AI</a><a href="#architecture"><span>09</span>Architecture</a>
   </nav>
   <div className="header-controls">
    <select aria-label="Machine" value={selectedMachineId} onChange={e=>setSelectedMachineId(e.target.value)}>{liveMachineOptions(machines).map((id:string)=><option key={id} value={id}>{id}</option>)}</select>
    <select aria-label="AI language" value={language} onChange={e=>setLanguage(e.target.value as Language)}><option value="auto">Auto / Hinglish</option><option value="en">English</option><option value="hi">हिन्दी</option><option value="hinglish">Hinglish</option></select>
    <button onClick={load}><RefreshCw size={16}/> Refresh</button>
   </div>
  </header>
  <div className="scroll-cue"><ChevronDown size={15}/><span>SCROLL TO EXPLORE</span></div>
  <aside className="command-rail" aria-label="Smart Factory command rail">
   <a href="#overview" title="Overview"><span>01</span><b>OV</b></a>
   <a href="#machine" title="Machine"><span>02</span><b>MC</b></a>
   <a href="#telemetry" title="Telemetry"><span>03</span><b>TL</b></a>
   <a href="#copilot" title="AI Copilot"><span>04</span><b>AI</b></a>
   <a href="#alerts" title="Alerts"><span>05</span><b>AL</b></a>
   <a href="#analytics" title="Analytics"><span>06</span><b>AN</b></a>
   <a href="#maintenance" title="Maintenance"><span>07</span><b>MT</b></a>
   <a href="#intelligence" title="Future AI"><span>08</span><b>FI</b></a>
   <a href="#architecture" title="Architecture"><span>09</span><b>AR</b></a>
  </aside>
  {error&&<div className="error">{error}</div>}
  <section id="overview" className="stack-section stack-overview">
   <div className="section-label"><span>01</span><Radio size={14}/> SYSTEM OVERVIEW</div>
   <div className="section-intro"><div><small>FACTORY COMMAND CENTER</small><h2>Live Industrial Intelligence</h2></div><span>REAL-TIME DATA PIPELINE</span></div>
   <section className="stats">
    <Card icon={<Activity/>} title="Telemetry Readings" value={summary?.readings??0}/>
    <Card icon={<Cpu/>} title="Active Machines" value={summary?.machines??0}/>
    <Card icon={<Gauge/>} title="Avg Failure Risk" value={`${((summary?.avg_failure_probability??0)*100).toFixed(1)}%`}/>
    <Card icon={<ShieldCheck/>} title="High Risk Events" value={summary?.high_risk_readings??0}/>
   </section>
  </section>
  <section id="machine" className="stack-section stack-machine">
   <div className="section-label"><span>02</span><Activity size={14}/> LIVE MACHINE MONITORING</div>
   <div className="section-intro"><div><small>SELECTED ASSET · LIVE</small><h2>{machine?.machine_id || "No machine"} intelligence</h2></div><span>REAL-TIME MACHINE STATE</span></div>
   <section className="grid">
   <div className="panel"><div className="head"><div><small>MACHINE</small><h2>{machine?.machine_id||"No machine"}</h2></div><span className={`badge ${(machine?.current_risk||"UNKNOWN").toLowerCase()}`}>{machine?.current_risk||"UNKNOWN"}</span></div>
    <div className="machine"><div><small>Prediction</small><b>{machine?.current_prediction||"N/A"}</b></div><div><small>Max Failure Risk</small><b>{((machine?.max_failure_probability||0)*100).toFixed(1)}%</b></div></div>
    <div className="metrics"><Metric icon={<Thermometer/>} name="Air" value={latest?.air_temperature?`${latest.air_temperature.toFixed(1)} K`:"--"}/><Metric icon={<Thermometer/>} name="Process" value={latest?.process_temperature?`${latest.process_temperature.toFixed(1)} K`:"--"}/><Metric icon={<Gauge/>} name="RPM" value={latest?.rotational_speed?.toFixed(0)||"--"}/><Metric icon={<Wrench/>} name="Torque" value={latest?.torque?`${latest.torque.toFixed(1)} Nm`:"--"}/></div>
   </div>
   <div className="panel machine-state-panel"><small>MACHINE HEALTH SIGNAL</small><h2>Live condition</h2><div className="status"><small>Current prediction</small><b>{machine?.current_prediction||"N/A"}</b></div><div className="status"><small>Failure probability</small><b>{((machine?.max_failure_probability||0)*100).toFixed(1)}%</b></div><div className="status"><small>Telemetry points</small><b>{history.length}</b></div></div>
   </section>
  </section>

  <section id="telemetry" className="stack-section stack-telemetry">
   <div className="section-label"><span>03</span><Radio size={14}/> LIVE TELEMETRY</div>
   <div className="section-intro"><div><small>TIME-SERIES INTELLIGENCE</small><h2>Failure probability over time</h2></div><span>LIVE STREAM</span></div>
   <section className="panel chart telemetry-panel"><div className="head"><div><small>LIVE TELEMETRY</small><h2>Failure Probability</h2></div><span className="live">LIVE</span></div><Suspense fallback={<div className="status">Loading chart...</div>}><TelemetryChart history={history}/></Suspense></section>
  </section>

  <section id="copilot" className="stack-section stack-copilot">
   <div className="section-label"><span>03</span><BrainCircuit size={14}/> AI MAINTENANCE COPILOT</div>
  <section className="panel" style={{marginTop:0}}>
   <div className="head">
    <div>
   <MachineMonitoring machine={machine} latest={latest} />
   <SensorIntelligence history={history} latest={latest} />
     <small>AI MAINTENANCE COPILOT</small>
     <h2>Maintenance Assessment</h2>
    </div>

    
     <button type="button" onClick={runAssessment} disabled={assessing}>{assessing?"Assessing...":"Run Assessment"}</button>
   </div>

   <div className="assistant-prompts"><small>AI ASSISTANT</small><div><button type="button" onClick={()=>setQuestion("Why is this machine considered low risk?")}>Why is this machine low risk?</button><button type="button" onClick={()=>setQuestion("What maintenance checks are relevant?")}>Maintenance checks</button><button type="button" onClick={()=>setQuestion("Which sensor values should I monitor?")}>Sensor guidance</button></div></div>
<div className="copilot-input"><input type="text" value={question} onChange={(e)=>setQuestion(e.target.value)} placeholder="Ask the maintenance copilot about this machine..." /><button type="button" onClick={runAssessment} disabled={assessing||!latest}>{assessing?"Analyzing...":"Analyze Machine"}</button></div>
       {ragAnswer && <div className="rag-result"><small>RAG KNOWLEDGE</small><b>{ragAnswer.answer}</b><span>Confidence: {(Number(ragAnswer.confidence||0)*100).toFixed(1)}%</span>{Array.isArray(ragAnswer.sources)&&ragAnswer.sources.length>0&&<div className="rag-sources">{ragAnswer.sources.map((src:any,i:number)=><div key={i}><small>Source {i+1}</small><span>{src.document} · p.{src.page}</span></div>)}</div>}</div>}

{!assessment && (
    <div className="status">
     <small>READY</small>
     <b>Run an AI assessment using the latest machine telemetry.</b>
    </div>
   )}

   {assessment && (
    <>
     <div className="machine">
      <div>
       <small>OVERALL RISK</small>
       <b>{assessment.overall_risk}</b>
      </div>

      <div>
       <small>FAILURE ASSESSMENT</small>
       <b>
        {assessment.failure_assessment?.prediction}
        {" · "}
        {Number(
         assessment.failure_assessment?.failure_probability_percent||0
        ).toFixed(2)}%
       </b>
      </div>

      <div>
       <small>RUL ASSESSMENT</small>
       <b>
        {assessment.rul_assessment?.available
         ?"Available"
         :"Unavailable for live telemetry"}
       </b>
      </div>
     </div>

     <div className="status">
      <small>MAINTENANCE ACTION</small>
      <b>{assessment.maintenance_action}</b>
     </div>

     <div className="status">
      <small>RISK EXPLANATION</small>
      <b>{assessment.risk_explanation}</b>
     </div>

     {assessment.rul_assessment?.reason && (
      <div className="status">
       <small>RUL NOTE</small>
       <b>{assessment.rul_assessment.reason}</b>
      </div>
     )}

     {assessment.evidence?.length > 0 && (
      <div className="status">
       <small>RAG EVIDENCE</small>

       {assessment.evidence.map((e:any,i:number)=>(
        <div key={i} style={{marginTop:8}}>
         <b>Page {e.page}</b>
         {" — "}
         {e.chunk_text}
        </div>
       ))}
      </div>
     )}
    </>
   )}
  </section>
  </section>

  <section id="alerts" className="stack-section stack-alerts">
   <div className="section-label"><span>04</span><ShieldCheck size={14}/> ALERTS & FACTORY HEALTH</div>
  <section className="panel alerts" style={{marginTop:0}}><div className="head"><div><small>ALERT CENTER</small><h2>Machine Alerts</h2></div><span className="system-status">LIVE MONITORING</span></div><div className="alert-list">{(summary?.high_risk_readings??0)>0?<div className="alert-item high"><span className="alert-dot"></span><div><b>High-risk machine condition detected</b><small>Immediate maintenance assessment recommended.</small></div><strong>{summary?.high_risk_readings}</strong></div>:(summary?.medium_risk_readings??0)>0?<div className="alert-item medium"><span className="alert-dot"></span><div><b>Medium-risk telemetry detected</b><small>Continue monitoring and schedule maintenance inspection.</small></div><strong>{summary?.medium_risk_readings}</strong></div>:<div className="alert-item clear"><span className="alert-dot"></span><div><b>No active alerts</b><small>Current telemetry is within the monitored risk thresholds.</small></div><strong>0</strong></div>}</div></section>

  <section id="analytics" className="panel analytics-shell" style={{marginTop:18}}>
   <div className="section-label"><span>05</span><Gauge size={14}/> ANALYTICS & MODEL STATUS</div>
  <section className="grid lower">
   <div className="panel"><small>RISK DISTRIBUTION</small><h2>Factory Health</h2><Row name="Low risk" value={summary?.low_risk_readings??0} cls="low"/><Row name="Medium risk" value={summary?.medium_risk_readings??0} cls="medium"/><Row name="High risk" value={summary?.high_risk_readings??0} cls="high"/></div>
   <div className="panel"><small>PREDICTIVE MAINTENANCE</small><h2>AI Model Status</h2><Status name="Failure Model" value="RandomForest · rf-industrial-v1"/><Status name="RUL Model" value="RandomForest · rf-rul-v1"/><Status name="RAG Engine" value="FAISS + BM25 · Ready"/><Status name="Sensor Pipeline" value="MQTT → TimescaleDB · Live"/></div>
  </section>
  <Suspense fallback={<div className={'status'}>Loading analytics...</div>}><Analytics summary={summary} history={history}/></Suspense>
  </section>
  </section>
  <section id="intelligence" className="stack-section stack-intelligence">
   <div className="section-label"><span>05</span><BrainCircuit size={14}/> FUTURE INTELLIGENCE</div>
   <FutureIntelligence machineId={selectedMachineId} language={language === "auto" ? "hinglish" : language} question={question} assessment={assessment}/>
  </section>
  <section id="architecture" className="stack-section stack-architecture">
   <div className="section-label"><span>06</span><Network size={14}/> INDUSTRIAL ARCHITECTURE</div>
   <FactoryArchitecture/>
   <Factory3D/>
  </section>
  <footer className="command-footer"><span>SMART FACTORY RAG</span><span>Industrial AI Command Center · Live telemetry connected</span></footer>
 </div>
}
function Card({icon,title,value}:{icon:any,title:string,value:any}){return <div className="stat">{icon}<div><small>{title}</small><strong>{value}</strong></div></div>}
function Metric({icon,name,value}:{icon:any,name:string,value:string}){return <div>{icon}<small>{name}</small><b>{value}</b></div>}
function Row({name,value,cls}:{name:string,value:number,cls:string}){return <div className="row"><i className={cls}></i><span>{name}</span><b>{value}</b></div>}
function Status({name,value}:{name:string,value:string}){return <div className="status"><small>{name}</small><b>{value}</b></div>}
function liveMachineOptions(items:any[]){return items.map((x:any)=>String(x.machine_id)).filter((id:string)=>id && id.toLowerCase()!=="derived")}




