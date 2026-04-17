from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="MedAI Backend")


class PatientData(BaseModel):
    age: int
    glucose: float
    bp: float


@app.get("/")
def home():
    return {"message": "MedAI Backend Running"}


@app.post("/predict")
def predict(data: PatientData):
    # Temporary demo logic. Replace with your trained model inference later.
    risk = "High Risk" if data.glucose > 150 else "Low Risk"
    return {
        "prediction": risk,
        "input": data,
    }
