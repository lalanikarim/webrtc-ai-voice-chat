import asyncio
from aiortc import MediaStreamTrack
from aiortc.contrib.media import MediaPlayer


class PlaybackStreamTrack(MediaStreamTrack):
    kind = "audio"
    response_ready: bool = False
    track: MediaStreamTrack = None
    counter: int = 0
    time: float = 0.0

    def __init__(self):
        super().__init__()  # don't forget this!

    def select_track(self):
        if self.response_ready:
            self.track = MediaPlayer("bark_out.wav", format="wav", loop=False).audio
        else:
            self.track = MediaPlayer("silence.wav", format="wav", loop=False).audio

    async def recv(self):
        self.counter += 1
        if self.track is None:
            self.select_track()
        try:
            async with asyncio.timeout(1):
                frame = await self.track.recv()
        except Exception as e:
            self.select_track()
            if self.response_ready:
                self.response_ready = False
            frame = await self.track.recv()

        if frame.pts < frame.sample_rate * self.time:
            frame.pts = frame.sample_rate * self.time
        self.time += 0.02
        return frame
