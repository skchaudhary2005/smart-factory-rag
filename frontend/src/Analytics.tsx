import { Activity, AlertTriangle, Gauge, TrendingUp } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function Analytics({summary,history=[]}:any){
 const rows=Array.isArray(history)?history:[];
 const avg=(key:string)=>{const v=rows.map((x:any)=>Number(x[key])).filter(Number.isFinite);return v.length?v.reduce((a:number,b:number)=>a+b,0)/v.length:0};
 const latest=rows[rows.length-1];
 return <section className="analytics panel">
  <div className="head"><div><small>PHASE 10 · ANALYTICS</small><h2>Factory Analytics</h2></div><span className="system-status">REAL DATA</span></div>
  <div className="analytics-cards">
   <div className="analytics-card"><Activity size={18}/><small>Samples</small><b>{summary?.readings??rows.length}</b></div>
   <div className="analytics-card"><TrendingUp size={18}/><small>Average Risk</small><b>{((summary?.avg_failure_probability??avg("failure_probability"))*100).toFixed(1)}%</b></div>
   <div className="analytics-card"><AlertTriangle size={18}/><small>Peak Risk</small><b>{((summary?.max_failure_probability??0)*100).toFixed(1)}%</b></div>
   <div className="analytics-card"><Gauge size={18}/><small>Average RPM</small><b>{avg("rotational_speed").toFixed(0)}</b></div>
  </div>
  <div className="analytics-chart">
   <div className="chart-title"><div><small>RISK TREND</small><h3>Failure Probability Over Time</h3></div><span>{latest?.failure_prediction||latest?.prediction||"LIVE"}</span></div>
   <ResponsiveContainer width="100%" height={300}>
    <LineChart data={rows}>
     <CartesianGrid strokeDasharray="3 3"/>
     <XAxis dataKey="time" tickFormatter={(v)=>new Date(v).toLocaleTimeString()}/>
     <YAxis tickFormatter={(v)=>`${(v*100).toFixed(0)}%`}/>
     <Tooltip formatter={(v:any)=>[`${(Number(v)*100).toFixed(2)}%`,"Failure Risk"]}/>
     <Line type="monotone" dataKey="failure_probability" strokeWidth={3} dot={false}/>
    </LineChart>
   </ResponsiveContainer>
  </div>
  <div className="analytics-grid">
   <div className="analytics-box"><small>TELEMETRY AVERAGES</small><h3>Operating Profile</h3><p>Air Temperature <b>{avg("air_temperature").toFixed(1)} K</b></p><p>Process Temperature <b>{avg("process_temperature").toFixed(1)} K</b></p><p>Rotational Speed <b>{avg("rotational_speed").toFixed(0)} RPM</b></p><p>Torque <b>{avg("torque").toFixed(1)} Nm</b></p></div>
   <div className="analytics-box"><small>RISK DISTRIBUTION</small><h3>Factory Risk Profile</h3><p>Low Risk <b>{summary?.low_risk_readings??0}</b></p><p>Medium Risk <b>{summary?.medium_risk_readings??0}</b></p><p>High Risk <b>{summary?.high_risk_readings??0}</b></p><p>Total Predictions <b>{summary?.failure_predictions??0}</b></p></div>
  </div>
 </section>
}