import { Activity, Gauge, Thermometer, Wrench } from "lucide-react";

export default function SensorIntelligence({ history = [], latest }: any) {
  const rows = Array.isArray(history) ? history : [];
  const avg = (key: string) => { const v=rows.map((x:any)=>Number(x[key])).filter(Number.isFinite); return v.length ? v.reduce((a:number,b:number)=>a+b,0)/v.length : Number(latest?.[key] ?? 0); };
  const sensor = [
    { icon:<Thermometer size={17}/>, name:'Air Temperature', key:'air_temperature', value:latest?.air_temperature, unit:'K' },
    { icon:<Thermometer size={17}/>, name:'Process Temperature', key:'process_temperature', value:latest?.process_temperature, unit:'K' },
    { icon:<Gauge size={17}/>, name:'Rotational Speed', key:'rotational_speed', value:latest?.rotational_speed, unit:'RPM' },
    { icon:<Wrench size={17}/>, name:'Torque', key:'torque', value:latest?.torque, unit:'Nm' },
  ];
  return <section className="panel sensor-intelligence">
    <div className="head"><div><small>SENSOR INTELLIGENCE</small><h2>Telemetry Health & Trends</h2></div><span className="system-status">ANALYZING</span></div>
    <div className="sensor-grid">
      {sensor.map((x:any)=><div className="sensor-card" key={x.key}>{x.icon}<small>{x.name}</small><b>{Number.isFinite(Number(x.value)) ? Number(x.value).toFixed(x.unit==='RPM'?0:1) : '--'} {x.unit}</b><span>Average: {Number(avg(x.key)).toFixed(x.unit==='RPM'?0:1)} {x.unit}</span></div>)}
    </div>
    <div className="sensor-footer"><Activity size={16}/><span>Telemetry samples analyzed</span><b>{rows.length}</b></div>
  </section>;
}
