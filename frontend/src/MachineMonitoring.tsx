import { Gauge, Thermometer, Wrench, Activity } from "lucide-react";

export default function MachineMonitoring({ machine, latest }: any) {
  return <section className="panel machine-monitoring">
    <div className="head">
      <div><small>MACHINE MONITORING</small><h2>Operating Parameters</h2></div>
      <span className="system-status">LIVE DATA</span>
    </div>
    <div className="monitor-grid">
      <div className="monitor-item"><Activity size={17}/><small>Machine ID</small><b>{machine?.machine_id || "--"}</b></div>
      <div className="monitor-item"><Gauge size={17}/><small>Rotational Speed</small><b>{latest?.rotational_speed?.toFixed(0) || "--"} RPM</b></div>
      <div className="monitor-item"><Thermometer size={17}/><small>Air Temperature</small><b>{latest?.air_temperature ? `${latest.air_temperature.toFixed(1)} K` : "--"}</b></div>
      <div className="monitor-item"><Thermometer size={17}/><small>Process Temperature</small><b>{latest?.process_temperature ? `${latest.process_temperature.toFixed(1)} K` : "--"}</b></div>
      <div className="monitor-item"><Wrench size={17}/><small>Torque</small><b>{latest?.torque ? `${latest.torque.toFixed(1)} Nm` : "--"}</b></div>
      <div className="monitor-item"><Wrench size={17}/><small>Tool Wear</small><b>{latest?.tool_wear?.toFixed(0) || "--"} min</b></div>
    </div>
  </section>;
}
