from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import time
from backend_functions import chat
from audio_processing import transcribing_chunks, transcribing_chunks_async
import json
from pydantic import BaseModel
import uvicorn

load_dotenv()
if os.path.exists(".env.local"):
    load_dotenv(".env.local")
if os.path.exists(".env.production") and os.getenv("ENVIRONMENT") == "production":
    load_dotenv(".env.production")

app = FastAPI()

# cors: https://fastapi.tiangolo.com/tutorial/cors/
frontend_url = os.getenv("FRONTEND_URL")
origins = [frontend_url]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/test")
def root():
    return {"msg": "fastapi is working"}


# https://www.starlette.io/websockets/
@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    # example async generator to test websocket streaming
    async def example_generator(data):
        for i in range(10):
            yield f"{data} + {i}"
            time.sleep(0.1)

    await websocket.accept()
    data = await websocket.receive_json()
    print(f"Received data: {data}")
    # send generator data to client
    async for value in example_generator(data["message"]):
        await websocket.send_json({"data": value})
    await websocket.send_json({"data": "completed"})
    # await websocket.close(code=1000, reason=None)


class PromptRequest(BaseModel):
    prompt: str
    history: list[dict]


@app.post("/chat")
def send_response(prompt_request: PromptRequest) -> None:
    prompt = prompt_request.prompt
    history = prompt_request.history
    print(f"Received prompt: {prompt}")
    print(f"Received history: {history}")
    print("not in streaming mode")
    # convert history to list of dict for chat function
    # time.sleep(0.2)
    # return {"content": f"{prompt.prompt}!", "author": "bot", "loading": False}
    response_message = chat(
        prompt=prompt,
        history=history,
        actor="personal assistant",
        max_tokens=500,
        accuracy="medium",
        stream=False,
        session_id="test_api",
    )
    print(f"response_message: {response_message}")
    return {"content": response_message["content"], "author": "bot", "loading": False}


# https://www.starlette.io/websockets/
@app.websocket("/chat/stream")
async def chat_stream(websocket: WebSocket):
    await websocket.accept()
    while True:
        prompt_request = await websocket.receive_json()
        prompt_request = PromptRequest(**prompt_request)
        prompt = prompt_request.prompt
        history = prompt_request.history
        print(f"Received prompt: {prompt}")
        print(f"Received history: {history}")
        print("in streaming mode")
        # get generator data to client
        response_generator = chat(
            prompt=prompt,
            history=history,
            actor="personal assistant",
            max_tokens=500,
            accuracy="medium",
            stream=True,
            session_id="test_api",
        )
        print("got response generator")
        for response_chunk in response_generator:
            chunk_message = response_chunk["choices"][0]["delta"]
            if "content" in chunk_message:
                await websocket.send_json({"content": chunk_message.content})
        await websocket.send_json({"content": "DONE"})


# https://www.starlette.io/websockets/
@app.websocket("/chat/stream/audioTranscript")
async def chat_stream(websocket: WebSocket):
    await websocket.accept()
    voice_chunks = []
    transcribed_segment_length = 0
    print("websocket connected")
    while True:
        voice_chunk = await websocket.receive_bytes()
        voice_chunks.append(voice_chunk)
        (
            transcripts,
            transcribed_segment_length,
            stop_transcribing,
        ) = await transcribing_chunks_async(voice_chunks, transcribed_segment_length)
        if stop_transcribing:
            # only 1 segment is used and only 1 transcript is returned
            transcript = transcripts[0]
            await websocket.send_json({"transcript": transcripts[0], "command": "DONE"})
            print(transcripts[0])
            print("disconnecting websocket...")
            # await websocket.close(code=1000, reason=None)
            voice_chunks = []
            transcribed_segment_length = 0
            stop_transcribing = False
            break
        else:
            for transcript in transcripts:
                print(transcript)
                await websocket.send_json({"transcript": transcript})


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8080, reload=False)