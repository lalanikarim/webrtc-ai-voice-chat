import argparse
import asyncio
import json
import logging
import os
import ssl
import threading
from asyncio import create_task, AbstractEventLoop
from typing import Optional

from aiohttp import web
from aiortc import RTCSessionDescription, MediaStreamTrack
from av import AudioFrame

from audio_utils import Whisper, Bark
from chain import Chain
from state import State

logger = logging.getLogger("pc")
ROOT = os.path.dirname(__file__)

pcs = set()

whisper: Optional[Whisper] = None
bark: Optional[Bark] = None
chain: Optional[Chain] = None


async def index(request):
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    content = open(os.path.join(ROOT, "client.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def css(request):
    content = open(os.path.join(ROOT, "styles.css"), "r").read()
    return web.Response(content_type="text/css", text=content)


async def offer(request):
    params = await request.json()

    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    state = State()
    pcs.add(state)

    state.log_info("Created for %s", request.remote)

    state.pc.addTrack(state.response_player)

    @state.pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        state.log_info("ICE connection state is %s", state.pc.iceConnectionState)
        if state.pc.iceConnectionState == "failed":
            await state.pc.close()

    async def record():
        track = state.track
        state.log_info("Recording %s", state.filename)
        while True:
            frame: AudioFrame = await track.recv()
            if state.recording:
                state.append_frame(frame)
            await asyncio.sleep(0)

    @state.pc.on("track")
    async def on_track(track: MediaStreamTrack):
        state.log_info("Track %s received", track.kind)

        if track.kind == "audio":
            state.log_info("Received %s", track.kind)
            state.track = track
            state.task = create_task(record())

        @track.on("ended")
        async def on_ended():
            state.log_info("Track %s ended", track.kind)
            state.task.cancel()
            track.stop()

    # handle offer
    await state.pc.setRemoteDescription(offer)

    # send answer
    answer = await state.pc.createAnswer()
    await state.pc.setLocalDescription(answer)

    @state.pc.on("datachannel")
    async def on_datachannel(channel):
        state.log_info("DataChannel")
        state.response_player.channel = channel

        @channel.on("message")
        async def on_message(message):
            state.log_info("Received message on channel: %s", message)
            if message == "get_response":
                state.response_player.response_ready = True
            if message == "get_silence":
                state.response_player.response_ready = False
            if message == "start_recording":
                state.log_info("Start Recording")
                state.response_player.response_ready = False
                state.buffer = []
                state.recording = True
                state.counter += 1
                state.filename = f"{state.id}_{state.counter}.wav"
            if message == "stop_recording":
                state.log_info("Stop Recording")
                state.recording = False
                await asyncio.sleep(0.5)
                data = state.flush_audio()
                process_loop = create_bg_loop()
                asyncio.run_coroutine_threadsafe(process_request(data), process_loop)
            if message[0:7] == "preset:":
                preset = message[7:]
                bark.set_voice_preset(preset)
                state.log_info("Changed voice preset to %s", preset)
            if message[0:6] == "model:":
                model = message[6:]
                chain.set_model(model)
                state.log_info("Changed model to %s", model)

        async def process_request(data):
            continue_to_synthesize, response = await transcribe_request(data)
            if continue_to_synthesize:
                response = response.strip().split("\n")[0]
                state.log_info(response)
                await synthesize_response(response)
            try:
                loop = asyncio.get_running_loop()
                loop.stop()
            finally:
                pass

        async def transcribe_request(data):
            response = None
            transcription = whisper.transcribe(data)
            channel.send(f"Human: {transcription[0]}")
            state.log_info(transcription[0])
            await asyncio.sleep(0)
            try:
                response = chain.get_chain().invoke({"human_input": transcription[0]})
                continue_to_synthesize = True
            except Exception as e:
                channel.send("AI: Error communicating with Ollama")
                channel.send(f"AI: {e}")
                channel.send("playing: response")
                channel.send("playing: silence")
                continue_to_synthesize = False
            return continue_to_synthesize, response

        async def synthesize_response(response):
            if len(response.strip()) > 0:
                channel.send(f"AI: {response}")
                await asyncio.sleep(0)
                bark.synthesize(response)
                state.response_player.response_ready = True
            else:
                channel.send("playing: response")
                channel.send("playing: silence")
            await asyncio.sleep(0)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": state.pc.localDescription.sdp, "type": state.pc.localDescription.type}
        ),
    )


async def on_shutdown(app):
    # close peer connections
    coros = [state.pc.close() for state in pcs]
    for state in pcs:
        deleteFile(state.filename)
    await asyncio.gather(*coros)


def deleteFile(filename):
    try:
        os.remove(filename)
    except OSError:
        pass


# https://gist.github.com/ultrafunkamsterdam/8be3d55ac45759aa1bd843ab64ce876d
def create_bg_loop():
    def to_bg(loop):
        asyncio.set_event_loop(loop)
        try:
            loop.run_forever()
        except asyncio.CancelledError as e:
            print('CANCELLEDERROR {}'.format(e))
        finally:
            for task in asyncio.all_tasks(loop):
                task.cancel()
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.stop()
            loop.close()

    new_loop = asyncio.new_event_loop()
    t = threading.Thread(target=to_bg, args=(new_loop,))
    t.start()
    return new_loop


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC AI Voice Chat")
    parser.add_argument("--cert-file", help="SSL certificate file (for HTTPS)")
    parser.add_argument("--key-file", help="SSL key file (for HTTPS)")
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host for HTTP server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port for HTTP server (default: 8080)"
    )
    parser.add_argument(
        "--ollama-host", default="http://localhost:11434", help="Ollama API Server (default: http://localhost:11434"
    )
    parser.add_argument(
        "--whisper-model", default="openai/whisper-small", help="Whisper model (default: openai/whisper-small)"
    )
    parser.add_argument(
        "--bark-model", default="suno/bark-small", help="Bark model (default: suno/bark-small)"
    )
    parser.add_argument("--verbose", "-v", action="count")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    chain = Chain()
    if args.ollama_host:
        chain.set_ollama_host(args.ollama_host)

    if args.whisper_model:
        whisper = Whisper(model_name=args.whisper_model)
    else:
        whisper = Whisper()

    if args.bark_model:
        bark = Bark(model_name=args.bark_model)
    else:
        bark = Bark()

    if args.cert_file:
        ssl_context = ssl.SSLContext()
        ssl_context.load_cert_chain(args.cert_file, args.key_file)
    else:
        ssl_context = None

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_get("/styles.css", css)
    app.router.add_post("/offer", offer)
    web.run_app(app, host=args.host, port=args.port, ssl_context=ssl_context)
