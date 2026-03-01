from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.models.schemas import HealthResponse
from api.routers import products, prices, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Price Tracker API",
    version="1.0.0",
    description="E-commerce product price tracking API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router, prefix="/api/v1")
app.include_router(prices.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()
