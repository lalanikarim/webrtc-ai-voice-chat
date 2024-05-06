import argparse
import asyncio
import copy
import json
import logging
import os
import ssl
import time
import uuid
from asyncio import create_task, Task

import librosa
from scipy.signal import resample

import numpy as np
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack, RTCDataChannel
from av import AudioFrame
from scipy.io import wavfile

logger = logging.getLogger("pc")
ROOT = os.path.dirname(__file__)

pcs = set()


class State:
    id: str
    filename: str
    pc: RTCPeerConnection
    dc: RTCDataChannel
    track: MediaStreamTrack
    # recorder: MediaRecorder
    buffer: list = []
    recording: bool = False
    task: Task
    sample_rate: int = 16000
    counter: int = 0


state = State()


async def index(request):
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    content = open(os.path.join(ROOT, "client.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def offer(request):
    params = await request.json()

    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    state.pc = RTCPeerConnection()
    state.id = str(uuid.uuid4())
    state.filename = f"{state.id}.wav"
    pcs.add(state)

    def log_info(msg, *args):
        logger.info(state.id + " " + msg, *args)

    log_info("Created for %s", request.remote)

    @state.pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        log_info("ICE connection state is %s", state.pc.iceConnectionState)
        if state.pc.iceConnectionState == "failed":
            await state.pc.close()

    async def record():
        track = state.track
        log_info("Recording %s", state.filename)
        while True:
            frame: AudioFrame = await track.recv()
            if state.recording:
                buffer = frame.to_ndarray().flatten().astype(np.int16)
                # check for silence
                max_abs = np.max(np.abs(buffer))
                if True or max_abs > 50:
                    if state.sample_rate != frame.sample_rate * 2:
                        state.sample_rate = frame.sample_rate * 2
                    state.buffer.append(buffer)
            await asyncio.sleep(0)

    @state.pc.on("track")
    async def on_track(track: MediaStreamTrack):
        log_info("Track %s received", track.kind)

        if track.kind == "audio":
            log_info("Received %s", track.kind)
            state.track = track
            state.task = create_task(record())

        @track.on("ended")
        async def on_ended():
            log_info("Track %s ended", track.kind)
            state.task.cancel()
            track.stop()

    # handle offer
    await state.pc.setRemoteDescription(offer)

    # send answer
    answer = await state.pc.createAnswer()
    await state.pc.setLocalDescription(answer)

    @state.pc.on("datachannel")
    async def on_datachannel(channel):
        log_info("DataChannel")
        state.dc = channel

        # state.dc.send("ready")

        @channel.on("message")
        async def on_message(message):
            log_info("Received message on channel: %s", message)
            if message == "start_recording":
                log_info("Start Recording")
                state.buffer = []
                state.recording = True
                state.counter += 1
                state.filename = f"{state.id}_{state.counter}.wav"
                channel.send(time.time().__str__())
            if message == "stop_recording":
                log_info("Stop Recording")
                state.recording = False
                await asyncio.sleep(0.5)
                state.buffer = np.array(state.buffer).flatten()
                log_info(f"Buffer Size: {len(state.buffer)}")
                # write to file
                data = copy.deepcopy(state.buffer)
                data = librosa.util.buf_to_float(data)
                state.buffer = []
                if state.sample_rate != 16000:
                    data = librosa.resample(data, orig_sr=state.sample_rate,
                                            target_sr=16000)
                wavfile.write(state.filename, 16000, data)
                channel.send(time.time().__str__())

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC server")
    parser.add_argument("--cert-file", help="SSL certificate file (for HTTPS)")
    parser.add_argument("--key-file", help="SSL key file (for HTTPS)")
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host for HTTP server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port for HTTP server (default: 8080)"
    )
    parser.add_argument("--verbose", "-v", action="count")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.cert_file:
        ssl_context = ssl.SSLContext()
        ssl_context.load_cert_chain(args.cert_file, args.key_file)
    else:
        ssl_context = None

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_post("/offer", offer)
    web.run_app(app, host=args.host, port=args.port, ssl_context=ssl_context)
