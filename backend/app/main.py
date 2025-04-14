import sys
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

# For Windows, use the ProactorEventLoopPolicy for better subprocess compatibility.
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(title="AI Agent Backend")

# Serve frontend static files if available.
try:
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
except Exception:
    @app.get("/")
    async def index():
        return {"message": "AI Agent is running."}

from app.agent import Agent

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    agent = Agent()  # Create a new agent instance per connection.
    try:
        while True:
            query = await websocket.receive_text()
            final_result = await agent.process(query)
            await websocket.send_text(final_result)
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
