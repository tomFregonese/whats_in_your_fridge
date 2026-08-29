/** Records microphone audio and encodes it as 16-bit PCM WAV.
 *
 * Deliberately not `MediaRecorder` — that only produces compressed formats
 * (webm/opus in Chrome/Firefox, mp4/aac in Safari) whose OpenRouter
 * support is unclear model-by-model, whereas the backend's multimodal
 * audio input (see `agent/dictation.py`) is only *guaranteed* to accept
 * `"wav"` or `"mp3"` by the OpenAI-compatible SDK it's built on. So this
 * captures raw PCM straight from the Web Audio API and builds a WAV file
 * by hand — sidesteps codec-support guesswork entirely, at the cost of
 * using the deprecated-but-still-universally-supported
 * `ScriptProcessorNode` (the modern replacement, `AudioWorkletNode`,
 * needs its own bundled worklet file — overkill for a short, infrequent
 * recording like this one).
 *
 * Also does simple energy-based voice-activity detection on the same raw
 * PCM it's already capturing (see `WavRecorderOptions`) — no separate
 * audio graph, no extra permission prompt. Deliberately not the Web
 * Speech API's built-in speech/sound-end events: this class exists
 * specifically to avoid that API (see `VoiceDictation.tsx`'s docstring —
 * worse cross-browser support, tied to a `lang` setting), so leaning on
 * it here for silence detection would reintroduce exactly what was
 * avoided. And not a trained VAD model (WebRTC/Silero) either — that's a
 * meaningfully bigger dependency for a feature that just needs "has the
 * user paused," not robust detection under hard background noise.
 */

// Ambient-noise sampling window right after `start()` — used to calibrate
// the silence threshold to the actual room/mic rather than a fixed guess.
const CALIBRATION_MS = 500;
// Speech must clear the calibrated noise floor by this factor to count as
// "not silence" — high enough that normal room tone doesn't trip it.
const NOISE_MULTIPLIER = 3;
// Floor under the calibrated threshold so a near-silent room (calibrated
// floor ~0) doesn't end up treating room tone as speech.
const ABSOLUTE_RMS_FLOOR = 0.01;
// Silence long enough to mark "this dictated item is done" — cuts a
// segment and keeps recording for the next one. Long enough to survive a
// mid-phrase breath, short enough that the next item starts promptly.
const DEFAULT_SEGMENT_SILENCE_MS = 700;
// Silence long enough to mark "done dictating entirely" — per the
// explicit product ask ("~2s").
const DEFAULT_AUTO_STOP_SILENCE_MS = 2000;

export interface WavRecorderOptions {
  /** Fires when speech is followed by `segmentSilenceMs` of silence: cuts
   * whatever's been captured since the last cut (or since `start()`) into
   * its own Blob and keeps recording seamlessly for the next item. Never
   * fires for a silence gap with no speech since the previous cut — a
   * pause before anything is said doesn't produce an empty segment. */
  onSegment?: (blob: Blob) => void;
  /** Fires once after `autoStopSilenceMs` of continuous silence — the
   * caller should treat this exactly like the user clicking the stop
   * button (see `VoiceDictation.tsx::finalizeRecording`). */
  onAutoStop?: () => void;
  segmentSilenceMs?: number;
  autoStopSilenceMs?: number;
}

export class WavRecorder {
  private audioContext: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private processor: ScriptProcessorNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private silence: GainNode | null = null;
  private chunks: Float32Array[] = [];

  private onSegment: ((blob: Blob) => void) | null = null;
  private onAutoStop: (() => void) | null = null;
  private segmentSilenceMs = DEFAULT_SEGMENT_SILENCE_MS;
  private autoStopSilenceMs = DEFAULT_AUTO_STOP_SILENCE_MS;
  private bufferDurationMs = 0;

  private calibrating = true;
  private calibrationRms: number[] = [];
  private calibrationElapsedMs = 0;
  private threshold = ABSOLUTE_RMS_FLOOR;

  private silenceMs = 0;
  private hasSpeechSinceCut = false;
  private segmentCutForCurrentSilence = false;
  private autoStopFiredForCurrentSilence = false;

  /** Requests mic access and starts capturing. Rejects if permission is
   * denied or no input device exists — the caller shows that as an error. */
  async start(options: WavRecorderOptions = {}): Promise<void> {
    this.onSegment = options.onSegment ?? null;
    this.onAutoStop = options.onAutoStop ?? null;
    this.segmentSilenceMs = options.segmentSilenceMs ?? DEFAULT_SEGMENT_SILENCE_MS;
    this.autoStopSilenceMs = options.autoStopSilenceMs ?? DEFAULT_AUTO_STOP_SILENCE_MS;

    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.audioContext = new AudioContext();
    this.source = this.audioContext.createMediaStreamSource(this.stream);
    // 4096 samples/buffer is the largest standard size — fewer, larger
    // callbacks for a recording that only lasts a few seconds anyway.
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
    this.bufferDurationMs = (4096 / this.audioContext.sampleRate) * 1000;
    this.chunks = [];
    this.calibrating = true;
    this.calibrationRms = [];
    this.calibrationElapsedMs = 0;
    this.silenceMs = 0;
    this.hasSpeechSinceCut = false;
    this.segmentCutForCurrentSilence = false;
    this.autoStopFiredForCurrentSilence = false;

    this.processor.onaudioprocess = (event) => {
      const samples = event.inputBuffer.getChannelData(0);
      this.chunks.push(new Float32Array(samples));
      this.processVoiceActivity(computeRms(samples));
    };

    // A `ScriptProcessorNode` only fires once it's part of a graph that
    // reaches the destination — route through a silenced gain node so the
    // mic doesn't also echo back out of the speakers.
    this.silence = this.audioContext.createGain();
    this.silence.gain.value = 0;
    this.source.connect(this.processor);
    this.processor.connect(this.silence);
    this.silence.connect(this.audioContext.destination);
  }

  /** Calibrates the silence threshold from the first `CALIBRATION_MS` of
   * audio, then tracks accumulated silence off every buffer afterward —
   * one continuous counter feeding both the segment-cut and auto-stop
   * thresholds, driven by the audio callback's own cadence rather than a
   * `setTimeout` (no drift, keeps ticking even if the tab throttles JS
   * timers in the background). */
  private processVoiceActivity(rms: number): void {
    if (this.calibrating) {
      this.calibrationRms.push(rms);
      this.calibrationElapsedMs += this.bufferDurationMs;
      if (this.calibrationElapsedMs >= CALIBRATION_MS) {
        this.threshold = Math.max(median(this.calibrationRms) * NOISE_MULTIPLIER, ABSOLUTE_RMS_FLOOR);
        this.calibrating = false;
      }
      return;
    }

    if (rms >= this.threshold) {
      this.silenceMs = 0;
      this.hasSpeechSinceCut = true;
      this.segmentCutForCurrentSilence = false;
      this.autoStopFiredForCurrentSilence = false;
      return;
    }

    this.silenceMs += this.bufferDurationMs;

    if (
      !this.segmentCutForCurrentSilence &&
      this.hasSpeechSinceCut &&
      this.silenceMs >= this.segmentSilenceMs
    ) {
      this.segmentCutForCurrentSilence = true;
      const blob = this.cutSegment();
      if (blob) this.onSegment?.(blob);
    }

    // Independent of whether a segment cut already fired for this same
    // silence stretch — this fires `autoStopSilenceMs` after the user
    // actually went quiet, not `autoStopSilenceMs` after their last cut.
    if (!this.autoStopFiredForCurrentSilence && this.silenceMs >= this.autoStopSilenceMs) {
      this.autoStopFiredForCurrentSilence = true;
      this.onAutoStop?.();
    }
  }

  /** Encodes whatever's been captured since the last cut (or since
   * `start()`) and resets the buffer to keep recording seamlessly.
   * Returns `null` if no speech was detected since the last cut — a
   * pause with nothing said yet shouldn't produce a request. */
  private cutSegment(): Blob | null {
    if (!this.hasSpeechSinceCut) return null;
    const wav = encodeWav(this.chunks, this.audioContext?.sampleRate ?? 44100);
    this.chunks = [];
    this.hasSpeechSinceCut = false;
    return wav;
  }

  /** Stops capturing and returns the trailing segment as a WAV `Blob` —
   * `null` if there's no unflushed speech to send (e.g. `onAutoStop`
   * already fired with everything already cut, or nothing was ever
   * said). */
  stop(): Blob | null {
    const wav = this.cutSegment();
    this.cleanup();
    return wav;
  }

  /** Stops capturing and discards it — used when the user cancels. */
  cancel(): void {
    this.cleanup();
  }

  private cleanup(): void {
    this.processor?.disconnect();
    this.source?.disconnect();
    this.silence?.disconnect();
    for (const track of this.stream?.getTracks() ?? []) track.stop();
    void this.audioContext?.close();
    this.processor = null;
    this.source = null;
    this.silence = null;
    this.stream = null;
    this.audioContext = null;
    this.chunks = [];
    this.onSegment = null;
    this.onAutoStop = null;
    this.calibrating = true;
    this.calibrationRms = [];
  }
}

function computeRms(samples: Float32Array): number {
  let sumOfSquares = 0;
  for (const sample of samples) sumOfSquares += sample * sample;
  return Math.sqrt(sumOfSquares / samples.length);
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

function encodeWav(chunks: Float32Array[], sampleRate: number): Blob {
  const sampleCount = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const merged = new Float32Array(sampleCount);
  let writeOffset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, writeOffset);
    writeOffset += chunk.length;
  }

  const bytesPerSample = 2; // 16-bit PCM
  const buffer = new ArrayBuffer(44 + sampleCount * bytesPerSample);
  const view = new DataView(buffer);

  writeAscii(view, 0, "RIFF");
  view.setUint32(4, 36 + sampleCount * bytesPerSample, true);
  writeAscii(view, 8, "WAVE");
  writeAscii(view, 12, "fmt ");
  view.setUint32(16, 16, true); // fmt chunk size
  view.setUint16(20, 1, true); // audio format: PCM
  view.setUint16(22, 1, true); // channel count: mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * bytesPerSample, true); // byte rate
  view.setUint16(32, bytesPerSample, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  writeAscii(view, 36, "data");
  view.setUint32(40, sampleCount * bytesPerSample, true);

  let pos = 44;
  for (const sample of merged) {
    const clamped = Math.max(-1, Math.min(1, sample));
    view.setInt16(pos, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
    pos += bytesPerSample;
  }

  return new Blob([buffer], { type: "audio/wav" });
}

function writeAscii(view: DataView, offset: number, text: string): void {
  for (let i = 0; i < text.length; i++) {
    view.setUint8(offset + i, text.charCodeAt(i));
  }
}

/** Base64-encodes a `Blob` for the JSON request body (`audio_base64`,
 * see `api/fridgeStock.ts::parseDictation`) — chunked to stay well under
 * engines' per-call argument limits for `String.fromCharCode`. */
export async function blobToBase64(blob: Blob): Promise<string> {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  const chunkSize = 0x8000;
  let binary = "";
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}
