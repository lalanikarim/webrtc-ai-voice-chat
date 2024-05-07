from typing import List

import torch
from scipy.io import wavfile
from transformers import WhisperProcessor, WhisperForConditionalGeneration, pipeline


class AudioUtils:
    def __init__(self, speech_to_text_model="openai/whisper-small", text_to_speech_model="suno/bark-small"):
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        # whisper
        self.speech_to_text_model_name = speech_to_text_model  # "openai/whisper-small"
        self.text_to_speech_model_name = text_to_speech_model  # "suno/bark-small"
        self.processor = WhisperProcessor.from_pretrained(self.speech_to_text_model_name, device=self.device)
        self.model = WhisperForConditionalGeneration.from_pretrained(self.speech_to_text_model_name).to(self.device)
        self.model.config.forced_decoder_ids = None
        # suno/bark
        self.synthesiser = pipeline("text-to-speech", self.text_to_speech_model_name, device=self.device)

    def transcribe(self, data) -> List[str]:
        input_features = self.processor(data, sampling_rate=16000,
                                        return_tensors="pt").input_features
        # generate token ids
        predicted_ids = self.model.generate(input_features)
        transcription = self.processor.batch_decode(predicted_ids, skip_special_tokens=True)
        return transcription

    def synthesize(self, text):
        speech = self.synthesiser(f"{text}", forward_params={"do_sample": True})
        wavfile.write("bark_out.wav", rate=speech["sampling_rate"], data=speech["audio"].T)
