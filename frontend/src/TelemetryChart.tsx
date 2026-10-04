import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function TelemetryChart({history=[]}:any){
 const rows=Array.isArray(history)?history:[];
 return <ResponsiveContainer width="100%" height={280}>
  <LineChart data={rows}>
   <CartesianGrid strokeDasharray="3 3"/>
   <XAxis dataKey="time" tickFormatter={(v)=>new Date(v).toLocaleTimeString()}/>
   <YAxis tickFormatter={(v)=>`${(v*100).toFixed(0)}%`}/>
   <Tooltip/>
   <Line type="monotone" dataKey="failure_probability" strokeWidth={3} dot={false}/>
  </LineChart>
 </ResponsiveContainer>;
}
