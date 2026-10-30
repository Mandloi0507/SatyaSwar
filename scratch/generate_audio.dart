import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

void main() {
  generateWav('assets/audio/calls/genuine_01.wav', 17.5, 220.0);
  generateWav('assets/audio/calls/clone_ceo_01.wav', 21.0, 330.0);
  generateWav('assets/audio/calls/noisy_01.wav', 17.5, 180.0, addNoise: true);
  generateWav(
    'assets/audio/calls/short_insufficient_01.wav',
    17.5,
    0.0,
    isSilence: true,
  );
  print('Generated 4 test WAV files successfully.');
}

void generateWav(
  String path,
  double durationSeconds,
  double baseFreq, {
  bool addNoise = false,
  bool isSilence = false,
}) {
  const sampleRate = 16000;
  const numChannels = 1;
  const bitsPerSample = 16;
  const bytesPerSample = 2;

  final numSamples = (sampleRate * durationSeconds).round();
  final dataSize = numSamples * numChannels * bytesPerSample;
  final fileSize = 36 + dataSize;

  final buffer = Uint8List(44 + dataSize);
  final bd = ByteData.sublistView(buffer);

  // RIFF Chunk Descriptor
  buffer.setRange(0, 4, 'RIFF'.codeUnits);
  bd.setUint32(4, fileSize, Endian.little);
  buffer.setRange(8, 12, 'WAVE'.codeUnits);

  // "fmt " Sub-chunk
  buffer.setRange(12, 16, 'fmt '.codeUnits);
  bd.setUint32(16, 16, Endian.little); // SubChunk1Size (16 for PCM)
  bd.setUint16(20, 1, Endian.little); // AudioFormat (1 = PCM)
  bd.setUint16(22, numChannels, Endian.little);
  bd.setUint32(24, sampleRate, Endian.little);
  bd.setUint32(
    28,
    sampleRate * numChannels * bytesPerSample,
    Endian.little,
  ); // ByteRate
  bd.setUint16(32, numChannels * bytesPerSample, Endian.little); // BlockAlign
  bd.setUint16(34, bitsPerSample, Endian.little);

  // "data" Sub-chunk
  buffer.setRange(36, 40, 'data'.codeUnits);
  bd.setUint32(40, dataSize, Endian.little);

  // Generate synthetic human speech formant frequencies (F0 harmonic series with gentle modulation)
  final rnd = Random(42);
  var offset = 44;
  for (var i = 0; i < numSamples; i++) {
    int sample = 0;
    if (!isSilence) {
      final t = i / sampleRate;
      // Speech modulation envelope (simulate words/pauses)
      final envelope = (sin(2 * pi * 2.5 * t) * 0.4 + 0.6).clamp(0.0, 1.0);

      // Formant synthesis (Fundamental frequency + harmonics)
      final f0 = sin(2 * pi * baseFreq * t);
      final f1 = 0.5 * sin(2 * pi * (baseFreq * 2.2) * t);
      final f2 = 0.25 * sin(2 * pi * (baseFreq * 3.8) * t);
      var val = (f0 + f1 + f2) * 0.4 * envelope;

      if (addNoise) {
        val += (rnd.nextDouble() * 2 - 1) * 0.15;
      }
      sample = (val.clamp(-1.0, 1.0) * 32767).round();
    }
    bd.setInt16(offset, sample, Endian.little);
    offset += 2;
  }

  File(path).writeAsBytesSync(buffer);
  print(
    'Wrote $path: $numSamples samples ($dataSize bytes, ${durationSeconds}s)',
  );
}
