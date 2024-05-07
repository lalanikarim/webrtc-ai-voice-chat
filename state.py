from asyncio import Task
import copy
import uuid

import librosa
import numpy as np
from aiortc import RTCPeerConnection, RTCDataChannel, MediaStreamTrack
from av import AudioFrame

from playback_stream_track import PlaybackStreamTrack
import logging


class State:
    track: MediaStreamTrack
    buffer: list = []
    recording: bool = False
    task: Task
    sample_rate: int = 16000
    counter: int = 0
    response_player: PlaybackStreamTrack = PlaybackStreamTrack()

    logger = logging.getLogger("pc")

    def __init__(self):
        self.pc = RTCPeerConnection()
        self.id = str(uuid.uuid4())
        self.filename = f"{self.id}.wav"

    def log_info(self, msg, *args):
        self.logger.info(self.id + " " + msg, *args)

    def append_frame(self, frame: AudioFrame):
        buffer = frame.to_ndarray().flatten().astype(np.int16)
        # check for silence
        max_abs = np.max(np.abs(buffer))
        if True or max_abs > 50:
            if self.sample_rate != frame.sample_rate * 2:
                self.sample_rate = frame.sample_rate * 2
            self.buffer.append(buffer)

    def flush_audio(self):
        self.buffer = np.array(self.buffer).flatten()
        self.log_info(f"Buffer Size: {len(self.buffer)}")
        # write to file
        data = copy.deepcopy(self.buffer)
        data = librosa.util.buf_to_float(data)
        self.buffer = []
        if self.sample_rate != 16000:
            data = librosa.resample(data, orig_sr=self.sample_rate,
                                    target_sr=16000)
        return data
