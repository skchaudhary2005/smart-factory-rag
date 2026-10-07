# 🏭 Smart Factory RAG

AI-powered predictive maintenance, sensor fusion, industrial analytics, digital-twin simulation, and Retrieval-Augmented Generation platform.

## 📌 Project Overview

Smart Factory RAG combines industrial telemetry, machine-failure prediction, maintenance intelligence, RAG-based technical assistance, anomaly detection, digital-twin what-if simulation, and future-intelligence features into one factory dashboard.

## 🎯 Objectives
- Monitor industrial machine telemetry
- Predict machine failure risk
- Support predictive maintenance
- Provide RAG-based industrial assistance
- Detect anomalies
- Perform digital-twin what-if simulations
- Prepare telemetry for edge/PLC integration

## 🚀 Features
- 📡 Industrial telemetry monitoring
- 🤖 Failure-risk prediction
- 🔧 Predictive maintenance
- 🔎 RAG with FAISS + BM25
- 🚨 Anomaly detection
- 🔔 Smart alerts
- 🧪 Digital Twin simulation
- ⏳ Remaining Useful Life (RUL) support
- 🧠 Model registry and challenger models
- 🗓️ Maintenance scheduling
- 👷 Technician feedback
- 🌐 Web dashboard
- 🔌 Industrial Edge Gateway layer

## 🏗️ Architecture

PLC / Sensors → Edge Gateway → MQTT → Smart Factory Backend → TimescaleDB → ML + RAG → Dashboard

The repository also supports simulation/industrial telemetry for demonstration and development.

## 🧠 AI / ML

The system includes industrial failure prediction and RUL components, with a model registry supporting a champion model and challenger models.

RAG combines vector and keyword retrieval to provide technical context to the application.

## 🔌 Edge Gateway

The repository includes an edge connector layer supporting:
- Simulator mode
- Modbus TCP read-only telemetry
- OPC-UA read-only telemetry
- MQTT publishing
- Sensor/tag normalization

The physical PLC integration requires the actual PLC model, protocol, network details, and tag/register mapping.

## 🧪 Digital Twin

The current Digital Twin functionality provides ML-based what-if simulation using machine operating parameters and failure-risk prediction. It is not presented as a full physics simulation.

## ⏳ RUL

The RUL model requires its complete feature set. The system does not fabricate missing sensor values; live RUL is available only when the required telemetry is present.

## 🛠️ Technology Stack
- Python
- FastAPI
- Pydantic
- PyTorch
- LightGBM
- FAISS
- BM25
- PostgreSQL / TimescaleDB
- MQTT
- Docker
- React / TypeScript frontend
- Render deployment

## 🌐 Deployment

The project is designed as a deployed backend + frontend system and can also be extended with an industrial edge gateway for real-machine telemetry.

## 🔮 Future Scope
- Real PLC/OPC-UA deployment
- Machine-specific model validation
- More industrial protocols
- Edge inference
- Real historical failure datasets
- Stronger industrial security
- Physics-based digital twin integration

## 👨‍💻 Author

**Sumit Kumar**


### 📬 Connect With Me
- GitHub: [skchaudhary2005](https://github.com/skchaudhary2005)
- LinkedIn: [Sumit Kumar](https://www.linkedin.com/in/sumit-chaudhary-41b306327/)

⭐ If you find this project useful, consider starring the repository.
