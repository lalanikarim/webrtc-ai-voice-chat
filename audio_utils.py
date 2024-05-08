from typing import List

import torch
from scipy.io import wavfile
from transformers import WhisperProcessor, WhisperForConditionalGeneration, AutoProcessor, BarkModel


class Whisper:
    def __init__(self, model_name="openai/whisper-small"):
        self.__device = "cuda:0" if torch.cuda.is_available() else "cpu"
        # whisper
        self.__model = WhisperForConditionalGeneration.from_pretrained(model_name).to(
            self.__device)
        self.__model.config.forced_decoder_ids = None
        self.__processor = WhisperProcessor.from_pretrained(model_name)

    def transcribe(self, data) -> List[str]:
        input_features = self.__processor(data, sampling_rate=16000,
                                          return_tensors="pt").input_features
        if self.__device != "cpu":
            input_features = input_features.to(self.__device, torch.float32)
        # generate token ids
        predicted_ids = self.__model.generate(input_features)
        transcription = self.__processor.batch_decode(predicted_ids, skip_special_tokens=True)
        return transcription


class Bark:
    def __init__(self, model_name="suno/bark-small", voice_preset="v2/en_speaker_0"):
        self.__device = "cuda:0" if torch.cuda.is_available() else "cpu"
        # suno/bark
        self.__model = BarkModel.from_pretrained(model_name).to(self.__device)
        self.__synthesiser = AutoProcessor.from_pretrained(model_name)
        self.__voice_preset = voice_preset

    def set_voice_preset(self, voice_preset):
        self.__voice_preset = voice_preset

    def synthesize(self, text):
        input_features = self.__synthesiser(f"{text}", voice_preset=self.__voice_preset).to(self.__device)
        audio_array = self.__model.generate(**input_features)
        if self.__device != "cpu":
            audio_array = audio_array.to(self.__device, torch.float32)
        audio_array = audio_array.cpu().numpy().squeeze()
        sample_rate = self.__model.generation_config.sample_rate
        wavfile.write("bark_out.wav", rate=sample_rate, data=audio_array)