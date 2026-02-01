from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import os
import json
import logging

# Import Core Engine and Gateway
from router_engine import RouterEngineV1
from llm_gateway import LLMGateway

app = FastAPI(title="Antigravity Router API", version="1.0.0")

# Initialize Engines
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

try:
    # Load with local ruleset
    router = RouterEngineV1(ruleset_path="ruleset.json")
    gateway = LLMGateway()
    logger.info("Router V1 Initialized Successfully")
except Exception as e:
    logger.error(f"Failed to initialize engines: {e}")
    raise e

# Request Schema
class RouteRequest(BaseModel):
    text: str
    channel: str = "web"
    product: str = "generic"
    metadata: Dict[str, Any] = {}
    execute_remote: bool = True # If true, Gateway executes the call

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "v1.frozen"}

@app.post("/route")
def route_traffic(req: RouteRequest):
    try:
        # 1. Get Deterministic Decision (Antigravity)
        input_data = req.dict()
        # Remap for engine compatibility (engine expects dict)
        decision = router.getRoute(input_data)
        
        # 2. Execute (Gateway) if requested
        if req.execute_remote:
            final_response = gateway.execute(decision, input_data)
            return final_response
        else:
            return decision

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Local dev run
    uvicorn.run(app, host="0.0.0.0", port=8000)
