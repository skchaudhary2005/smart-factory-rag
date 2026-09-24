import os
from fastapi import APIRouter, HTTPException
import psycopg

router = APIRouter(prefix="/analytics", tags=["Analytics"])
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://factory:factory@postgres:5432/smartfactory")

def db():
    return psycopg.connect(DATABASE_URL)

@router.get("/summary")
def summary():
    with db() as conn:
        row = conn.execute("""SELECT COUNT(*) AS readings, COUNT(DISTINCT machine_id) AS machines, COALESCE(AVG(failure_probability),0) AS avg_failure_probability, COALESCE(MAX(failure_probability),0) AS max_failure_probability, COUNT(*) FILTER (WHERE prediction='FAILURE_RISK') AS failure_predictions, COUNT(*) FILTER (WHERE risk_level='HIGH') AS high_risk_readings, COUNT(*) FILTER (WHERE risk_level='MEDIUM') AS medium_risk_readings, COUNT(*) FILTER (WHERE risk_level='LOW') AS low_risk_readings FROM sensor_readings""").fetchone()
    return {"readings": row[0], "machines": row[1], "avg_failure_probability": round(float(row[2]),6), "max_failure_probability": round(float(row[3]),6), "failure_predictions": row[4], "high_risk_readings": row[5], "medium_risk_readings": row[6], "low_risk_readings": row[7]}

@router.get("/machines")
def machines():
    with db() as conn:
        rows = conn.execute("""SELECT machine_id, COUNT(*) AS readings, MAX(time) AS last_seen, AVG(failure_probability) AS avg_failure_probability, MAX(failure_probability) AS max_failure_probability, (array_agg(risk_level ORDER BY time DESC))[1] AS current_risk, (array_agg(prediction ORDER BY time DESC))[1] AS current_prediction FROM sensor_readings GROUP BY machine_id ORDER BY machine_id""").fetchall()
    return {"machines": [{"machine_id":r[0],"readings":r[1],"last_seen":r[2],"avg_failure_probability":round(float(r[3]),6),"max_failure_probability":round(float(r[4]),6),"current_risk":r[5],"current_prediction":r[6]} for r in rows]}

@router.get("/machines/{machine_id}")
def machine(machine_id: str):
    with db() as conn:
        r = conn.execute("""SELECT machine_id, COUNT(*) AS readings, MIN(time), MAX(time), AVG(air_temperature), AVG(process_temperature), AVG(rotational_speed), AVG(torque), AVG(tool_wear), AVG(failure_probability), MAX(failure_probability), (array_agg(risk_level ORDER BY time DESC))[1], (array_agg(prediction ORDER BY time DESC))[1], (array_agg(model_version ORDER BY time DESC))[1] FROM sensor_readings WHERE machine_id=%s GROUP BY machine_id""", (machine_id,)).fetchone()
    if not r: raise HTTPException(status_code=404, detail=f"Machine {machine_id} not found")
    return {"machine_id":r[0],"readings":r[1],"first_seen":r[2],"last_seen":r[3],"avg_air_temperature":r[4],"avg_process_temperature":r[5],"avg_rotational_speed":r[6],"avg_torque":r[7],"avg_tool_wear":r[8],"avg_failure_probability":r[9],"max_failure_probability":r[10],"current_risk":r[11],"current_prediction":r[12],"model_version":r[13]}

@router.get("/machines/{machine_id}/history")
def history(machine_id: str, limit: int = 100):
    limit = max(1, min(limit, 1000))
    with db() as conn:
        rows = conn.execute("""SELECT time, machine_type, air_temperature, process_temperature, rotational_speed, torque, tool_wear, failure_probability, prediction, risk_level, model_version FROM sensor_readings WHERE machine_id=%s ORDER BY time DESC LIMIT %s""", (machine_id, limit)).fetchall()
    return {"machine_id":machine_id,"count":len(rows),"history":[{"time":r[0],"machine_type":r[1],"air_temperature":r[2],"process_temperature":r[3],"rotational_speed":r[4],"torque":r[5],"tool_wear":r[6],"failure_probability":r[7],"prediction":r[8],"risk_level":r[9],"model_version":r[10]} for r in rows]}

@router.get("/machines/{machine_id}/risk")
def risk(machine_id: str, limit: int = 100):
    limit = max(1, min(limit, 1000))
    with db() as conn:
        rows = conn.execute("SELECT time, failure_probability, prediction, risk_level FROM sensor_readings WHERE machine_id=%s ORDER BY time DESC LIMIT %s", (machine_id, limit)).fetchall()
    return {"machine_id":machine_id,"count":len(rows),"risk_history":[{"time":r[0],"failure_probability":r[1],"prediction":r[2],"risk_level":r[3]} for r in rows]}
