from typing import List

import torch
from scipy.io import wavfile
from transformers import WhisperProcessor, WhisperForConditionalGeneration, AutoProcessor, BarkModel


class AudioUtils:
    def __init__(self, speech_to_text_model="openai/whisper-small", text_to_speech_model="suno/bark-small", voice_preset="v2/en_speaker_0"):
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        # whisper
        self.speech_to_text_model_name = speech_to_text_model  # "openai/whisper-small"
        self.text_to_speech_model_name = text_to_speech_model  # "suno/bark-small"
        self.processor = WhisperProcessor.from_pretrained(self.speech_to_text_model_name)
        self.stt_model = WhisperForConditionalGeneration.from_pretrained(self.speech_to_text_model_name).to(self.device)
        self.stt_model.config.forced_decoder_ids = None
        # suno/bark
        self.tta_model = BarkModel.from_pretrained(self.text_to_speech_model_name).to(self.device)
        self.synthesiser = AutoProcessor.from_pretrained(self.text_to_speech_model_name)
        self.voice_preset = voice_preset
        #self.synthesiser = pipeline("text-to-speech", self.text_to_speech_model_name, device=self.device, voice_preset="v2/en_speaker_1")

    def transcribe(self, data) -> List[str]:
        input_features = self.processor(data, sampling_rate=16000,
                                        return_tensors="pt").input_features
        if self.device != "cpu":
            input_features = input_features.to(self.device, torch.float32)
        # generate token ids
        predicted_ids = self.stt_model.generate(input_features)
        transcription = self.processor.batch_decode(predicted_ids, skip_special_tokens=True)
        return transcription

    def synthesize(self, text):
        input_features = self.synthesiser(f"{text}", voice_preset=self.voice_preset).to(self.device)
        audio_array = self.tta_model.generate(**input_features)
        if self.device != "cpu":
            audio_array = audio_array.to(self.device, torch.float32)
        audio_array = audio_array.cpu().numpy().squeeze()
        sample_rate = self.tta_model.generation_config.sample_rate
        wavfile.write("bark_out.wav", rate=sample_rate, data=audio_array)
