"""
SmartFactory-RAG API â€” Unified gateway for RAG, predictions, and sensor data.
"""

from __future__ import annotations
from src.api.analytics import router as analytics_router
import asyncio

import logging
import time
from contextlib import asynccontextmanager
from typing import Optional
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# â”€â”€ Schemas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    rerank: bool = False
    language: Optional[str] = None  # "el", "en", or auto-detect

class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    confidence: float
    retrieval_time_ms: float
    generation_time_ms: float

class PredictRequest(BaseModel):
    equipment_id: str
    window_size: int = Field(default=60, ge=10, le=500)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

class PredictResponse(BaseModel):
    equipment_id: str
    failure_probability: float
    severity: str
    time_to_failure_hours: Optional[float]
    root_cause: str
    recommended_action: str
    contributing_sensors: list[dict]

class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    components: dict


# â”€â”€ Application â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_start_time = time.time()
_rag_engine = None
_predictor = None
_ingester = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize components on startup."""
    global _rag_engine, _predictor, _ingester

    from src.rag.engine import RAGEngine
    from src.ml.predictor import FailurePredictor
    from src.sensors.ingester import SensorIngester

    logger.info("Initializing SmartFactory-RAG components...")

    try:
        _rag_engine = RAGEngine(index_path="/app/data/index")
        logger.info("RAG engine initialized")
    except Exception as e:
        logger.warning(f"RAG engine not available: {e}")

    try:
        _predictor = FailurePredictor.load("./models/latest")
        logger.info("Failure predictor loaded")
    except Exception as e:
        logger.warning(f"Predictor not available: {e}")

    _ingester = SensorIngester(
        mqtt_broker=os.getenv("MQTT_BROKER", "mqtt://localhost:1883"),
        topics=["factory/#"],
    )

    ingestion_task = asyncio.create_task(_ingester.start())

    yield

    if _ingester:
        await _ingester.stop()


app = FastAPI(

    title="SmartFactory-RAG",
    description="Intelligent Manufacturing Assistant â€” RAG + Predictive Maintenance + Sensor Fusion",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://localhost:5174"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# â”€â”€ Endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.get("/health", response_model=HealthResponse)
async def health():
    """System health check with component status."""
    return HealthResponse(
        status="healthy",
        uptime_seconds=round(time.time() - _start_time, 1),
        components={
            "rag_engine": "ready" if _rag_engine else "unavailable",
            "predictor": "ready" if _predictor else "unavailable",
            "sensor_ingester": "running" if _ingester and _ingester._running else "stopped",
        },
    )


@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Query equipment manuals and documentation using natural language.

    Returns an answer with traceable sources (document, page, paragraph).
    """
    if _rag_engine is None:
        raise HTTPException(503, "RAG engine not initialized. Index documents first.")

    result = _rag_engine.query(
        question=request.question,
        top_k=request.top_k,
        rerank=request.rerank,
    )

    return QueryResponse(
        answer=result.answer,
        sources=[
            {
                "document": s.document,
                "page": s.page,
                "paragraph": s.paragraph,
                "excerpt": s.chunk_text,
                "relevance_score": s.score,
            }
            for s in result.sources
        ],
        confidence=result.confidence,
        retrieval_time_ms=round(result.retrieval_time_ms, 1),
        generation_time_ms=round(result.generation_time_ms, 1),
    )


@app.post("/predict", response_model=PredictResponse)
async def predict_failure(request: PredictRequest):
    """
    Predict equipment failure from recent sensor data.

    Uses ensemble of LSTM + LightGBM models on the sensor window.
    """
    if _predictor is None:
        raise HTTPException(503, "Predictor not loaded. Train models first.")

    if _ingester is None:
        raise HTTPException(503, "Sensor ingester not running.")

    sensor_window = _ingester.get_window(
        request.equipment_id,
        size=request.window_size,
    )

    if sensor_window is None or len(sensor_window) < 10:
        raise HTTPException(
            404,
            f"Insufficient sensor data for equipment '{request.equipment_id}'. "
            f"Need at least 10 readings.",
        )

    prediction = _predictor.predict(
        sensor_window=sensor_window,
        confidence_threshold=request.confidence_threshold,
    )

    return PredictResponse(
        equipment_id=request.equipment_id,
        failure_probability=prediction.failure_probability,
        severity=prediction.severity,
        time_to_failure_hours=prediction.time_to_failure_hours,
        root_cause=prediction.root_cause,
        recommended_action=prediction.recommended_action,
        contributing_sensors=prediction.contributing_sensors,
    )


@app.get("/sensors/{equipment_id}/stats")
async def sensor_stats(equipment_id: str):
    """Get real-time sensor statistics for an equipment."""
    if _ingester is None:
        raise HTTPException(503, "Sensor ingester not running.")

    buffer = _ingester._buffers.get(equipment_id)
    if buffer is None:
        raise HTTPException(404, f"No data for equipment '{equipment_id}'")

    return {
        "equipment_id": equipment_id,
        "stats": buffer.stats(),
        "sensor_names": _ingester.SENSOR_NAMES,
    }


@app.get("/sensors/status")
async def ingestion_status():
    """Get sensor ingestion pipeline status."""
    if _ingester is None:
        return {"status": "not_initialized"}
    return _ingester.get_stats()


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)




class IndustrialPredictionRequest(BaseModel):
    machine_type: str
    air_temperature: float
    process_temperature: float
    rotational_speed: float
    torque: float
    tool_wear: float


class IndustrialPredictionResponse(BaseModel):
    prediction: str
    failure_probability: float
    failure_probability_percent: float
    risk_level: str
    model: str
    model_version: str


@app.post("/industrial/predict", response_model=IndustrialPredictionResponse)
async def industrial_predict(request: IndustrialPredictionRequest):
    try:
        from src.industrial_ai.predict import predict_failure as _industrial_predict_failure
        return _industrial_predict_failure(
            machine_type=request.machine_type,
            air_temperature=request.air_temperature,
            process_temperature=request.process_temperature,
            rotational_speed=request.rotational_speed,
            torque=request.torque,
            tool_wear=request.tool_wear,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Industrial prediction failed: {exc}")

class RULPredictionRequest(BaseModel):
    op_setting_1: float
    op_setting_2: float
    op_setting_3: float
    sensors: list[float]


class RULPredictionResponse(BaseModel):
    predicted_rul_cycles: float
    risk_level: str
    model: str
    model_version: str


@app.post("/industrial/rul", response_model=RULPredictionResponse)
async def industrial_rul(request: RULPredictionRequest):
    try:
        from src.industrial_ai.rul_predict import predict_rul
        return predict_rul(
            request.op_setting_1,
            request.op_setting_2,
            request.op_setting_3,
            request.sensors,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RUL prediction failed: {exc}")



class MaintenanceAssessmentRequest(BaseModel):
    machine_type: str
    air_temperature: float
    process_temperature: float
    rotational_speed: float
    torque: float
    tool_wear: float
    op_setting_1: float
    op_setting_2: float
    op_setting_3: float
    sensors: list[float]
    question: str = 'What maintenance checks are relevant for this machine based on the current condition?'


class MaintenanceAssessmentResponse(BaseModel):
    overall_risk: str
    failure_assessment: dict
    rul_assessment: dict
    maintenance_action: str
    evidence: list[dict]


@app.post('/industrial/maintenance-assessment', response_model=MaintenanceAssessmentResponse)
async def industrial_maintenance_assessment(request: MaintenanceAssessmentRequest):
    try:
        from src.industrial_ai.predict import predict_failure
        from src.industrial_ai.rul_predict import predict_rul
        failure = predict_failure(machine_type=request.machine_type, air_temperature=request.air_temperature, process_temperature=request.process_temperature, rotational_speed=request.rotational_speed, torque=request.torque, tool_wear=request.tool_wear)
        rul = predict_rul(request.op_setting_1, request.op_setting_2, request.op_setting_3, request.sensors)
        levels = {failure['risk_level'], rul['risk_level']}
        if 'HIGH' in levels:
            overall_risk = 'HIGH'
            action = 'Prioritize inspection. Check machine operating conditions and relevant motor protection components before continued operation.'
        elif 'MEDIUM' in levels:
            overall_risk = 'MEDIUM'
            action = 'Schedule a maintenance inspection and monitor the machine closely for deterioration.'
        else:
            overall_risk = 'LOW'
            action = 'Continue monitoring under normal maintenance procedures.'
        evidence = []
        if _rag_engine is not None:
            try:
                rag = _rag_engine.query(request.question, top_k=3, rerank=False)
                evidence = [{'document': x.document, 'page': x.page, 'paragraph': x.paragraph, 'score': x.score, 'chunk_text': x.chunk_text} for x in rag.sources[:3]]
            except Exception as exc:
                logger.warning('Maintenance RAG evidence unavailable: %s', exc)
        return {'overall_risk': overall_risk, 'failure_assessment': failure, 'rul_assessment': rul, 'maintenance_action': action, 'evidence': evidence}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Maintenance assessment failed: {exc}')


app.include_router(analytics_router)
