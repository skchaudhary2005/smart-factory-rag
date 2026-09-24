import { useEffect, useState } from "react";
import { Activity, Cpu, Gauge, RefreshCw, ShieldCheck, Thermometer, Wrench } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import "./App.css";

const API="http://localhost:8000";

export default function App(){
 const [summary,setSummary]=useState<any>(null);
 const [machines,setMachines]=useState<any[]>([]);
 const [history,setHistory]=useState<any[]>([]);
 const [error,setError]=useState("");
 const load=async()=>{
  try{
   setError("");
   const [a,b]=await Promise.all([fetch(`${API}/analytics/summary`),fetch(`${API}/analytics/machines`)]);
   if(!a.ok||!b.ok)throw Error("Backend API unavailable");
   const s=await a.json(),m=await b.json();
   setSummary(s);setMachines(m.machines||[]);
   if(m.machines?.length){const h=await fetch(`${API}/analytics/machines/${m.machines[0].machine_id}/history?limit=50`);if(h.ok){const x=await h.json();setHistory((x.history||[]).reverse())}}
  }catch(e){setError(e instanceof Error?e.message:"Connection error")}
 };
 useEffect(()=>{load();const t=setInterval(load,5000);return()=>clearInterval(t)},[]);
 const machine=machines[0],latest=history[history.length-1];
 const [assessment,setAssessment]=useState<any>(null);
 const [assessing,setAssessing]=useState(false);

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
    question:"What maintenance action is recommended for the current machine condition?"
   };

   const response=await fetch(
    `${API}/industrial/maintenance-assessment`,
    {
     method:"POST",
     headers:{"Content-Type":"application/json"},
     body:JSON.stringify(payload)
    }
   );

   if(!response.ok){
    throw Error("Maintenance assessment failed");
   }

   setAssessment(await response.json());
  }catch(e){
   setError(e instanceof Error?e.message:"Maintenance assessment failed");
  }finally{
   setAssessing(false);
  }
 };

 return <div className="app">
  <header><div><div className="eyebrow">INDUSTRIAL AI PLATFORM</div><h1>Smart Factory Monitor</h1><p>Predictive maintenance & real-time machine intelligence</p></div><button onClick={load}><RefreshCw size={16}/> Refresh</button></header>
  {error&&<div className="error">{error}</div>}
  <section className="stats">
   <Card icon={<Activity/>} title="Telemetry Readings" value={summary?.readings??0}/>
   <Card icon={<Cpu/>} title="Active Machines" value={summary?.machines??0}/>
   <Card icon={<Gauge/>} title="Avg Failure Risk" value={`${((summary?.avg_failure_probability??0)*100).toFixed(1)}%`}/>
   <Card icon={<ShieldCheck/>} title="High Risk Events" value={summary?.high_risk_readings??0}/>
  </section>
  <section className="grid">
   <div className="panel"><div className="head"><div><small>MACHINE</small><h2>{machine?.machine_id||"No machine"}</h2></div><span className={`badge ${(machine?.current_risk||"UNKNOWN").toLowerCase()}`}>{machine?.current_risk||"UNKNOWN"}</span></div>
    <div className="machine"><div><small>Prediction</small><b>{machine?.current_prediction||"N/A"}</b></div><div><small>Max Failure Risk</small><b>{((machine?.max_failure_probability||0)*100).toFixed(1)}%</b></div></div>
    <div className="metrics"><Metric icon={<Thermometer/>} name="Air" value={latest?.air_temperature?`${latest.air_temperature.toFixed(1)} K`:"--"}/><Metric icon={<Thermometer/>} name="Process" value={latest?.process_temperature?`${latest.process_temperature.toFixed(1)} K`:"--"}/><Metric icon={<Gauge/>} name="RPM" value={latest?.rotational_speed?.toFixed(0)||"--"}/><Metric icon={<Wrench/>} name="Torque" value={latest?.torque?`${latest.torque.toFixed(1)} Nm`:"--"}/></div>
   </div>
   <div className="panel chart"><div className="head"><div><small>LIVE TELEMETRY</small><h2>Failure Probability</h2></div><span className="live">● LIVE</span></div><ResponsiveContainer width="100%" height={280}><LineChart data={history}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="time" tickFormatter={v=>new Date(v).toLocaleTimeString()}/><YAxis tickFormatter={v=>`${(v*100).toFixed(0)}%`}/><Tooltip/><Line type="monotone" dataKey="failure_probability" strokeWidth={3} dot={false}/></LineChart></ResponsiveContainer></div>
  </section>

  <section className="panel" style={{marginTop:24}}>
   <div className="head">
    <div>
     <small>AI MAINTENANCE COPILOT</small>
     <h2>Maintenance Assessment</h2>
    </div>

    <button onClick={runAssessment} disabled={assessing}>
     {assessing?"Assessing...":"Run Assessment"}
    </button>
   </div>

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

  <section className="grid lower">
   <div className="panel"><small>RISK DISTRIBUTION</small><h2>Factory Health</h2><Row name="Low risk" value={summary?.low_risk_readings??0} cls="low"/><Row name="Medium risk" value={summary?.medium_risk_readings??0} cls="medium"/><Row name="High risk" value={summary?.high_risk_readings??0} cls="high"/></div>
   <div className="panel"><small>PREDICTIVE MAINTENANCE</small><h2>AI Model Status</h2><Status name="Failure Model" value="RandomForest · rf-industrial-v1"/><Status name="RUL Model" value="RandomForest · rf-rul-v1"/><Status name="RAG Engine" value="FAISS + BM25 · Ready"/><Status name="Sensor Pipeline" value="MQTT → TimescaleDB · Live"/></div>
  </section>
  <footer>Smart Factory RAG · Industrial AI Monitoring</footer>
 </div>
}
function Card({icon,title,value}:{icon:any,title:string,value:any}){return <div className="stat">{icon}<div><small>{title}</small><strong>{value}</strong></div></div>}
function Metric({icon,name,value}:{icon:any,name:string,value:string}){return <div>{icon}<small>{name}</small><b>{value}</b></div>}
function Row({name,value,cls}:{name:string,value:number,cls:string}){return <div className="row"><i className={cls}></i><span>{name}</span><b>{value}</b></div>}
function Status({name,value}:{name:string,value:string}){return <div className="status"><small>{name}</small><b>{value}</b></div>}
