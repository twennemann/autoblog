# %%
import wave
import json
from vosk import Model, KaldiRecognizer

def transcribe(wav_file):
    wf = wave.open(wav_file, "rb")
    model = Model(r"C:\Users\twenn\Documents\GitHub\wav_to_text\model\vosk-model-de-0.21")
    rec = KaldiRecognizer(model, wf.getframerate())

    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        rec.AcceptWaveform(data)

    result = json.loads(rec.Result())
    return result

# Beispielaufruf
wav_file = r"C:\Users\twenn\Documents\GitHub\wav_to_text\wav_examples\Vorstellungsgestraech.wav"
result = transcribe(wav_file)
print(json.dumps(result, indent=4))

# %%
