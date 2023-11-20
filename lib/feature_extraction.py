# TODO: create mfccs extraction with possibility to have:
#   - deltas (both or only first)
#   - summarised by utterance
from typing import Tuple
import numpy as np
import librosa
import parselmouth

# TODO: create function to extract mfccs (and delta-delta) from audio file


# helper of mel_features() to extract delta and delta-delta coefficients
def _delta_delta(mfccs: np.ndarray) -> np.ndarray:
    """
    Computes delta and delta-delta coefficients from MFCCs.

    Parameters:
    -----------
    mfccs : np.ndarray
        MFCCs for each frame in the audio file.

    Returns:
    --------
    features_vec : np.ndarray
        updated features vector containing MFCCs, deltas, and delta-deltas
        for each frame in the audio file. Shape is (n_frames, n_mfccs*3).
    """
    # compute delta and delta-delta
    delta = librosa.feature.delta(mfccs, order=1)
    delta_delta = librosa.feature.delta(mfccs, order=2)

    # concatenate features
    features_vec = np.concatenate((mfccs, delta, delta_delta), axis=0)

    return features_vec


# helper of mel_features() to summarise mfccs by utterance
def _summarise_features(features_vec: np.ndarray) -> np.ndarray:
    """
    Summarises MFCCs by utterance.

    Parameters:
    -----------
    features_vec : np.ndarray
        MFCCs (and delta-delta features) for each frame in the audio file.

    Returns:
    --------
    np.ndarray
        Mean and standard deviation of features for each utterance. Shape is
        (n_features*2,)
    """
    return np.concatenate(
        (np.mean(features_vec, axis=1), np.std(features_vec, axis=1)), axis=0
    )


# MFCCs extraction
def mel_features(
    audio_file: str,
    n_mfcc: int = 13,
    n_mels: int = 40,
    win_length: float = 25,
    overlap: float = 10,
    fmin: int = 150,
    fmax: int = 4000,
    premphasis: float = 0.95,
    lifter: int = 22,
    deltas: bool = False,
    summarise: bool = False
) -> np.ndarray:
    """
    Extracts mfccs (and optionally delta-delta) from audio file.

    Parameters:
    -----------
    audio_file : str
        Path to audio file.
    n_mfcc : int
        Number of MFCCs to return.
    n_mels : int
        Number of mel bands to generate.
    win_length : float
        Window length in milliseconds.
    overlap : float
        Overlap length in milliseconds.
    fmin : int
        Minimum frequency in mel filterbank in Hz.
    fmax : int
        Maximum frequency in mel filterbank in Hz.
    premphasis : float
        Coefficient for pre-emphasis filter.
    lifter : int
        Liftering coefficient.
    deltas : bool
        Whether to return delta and delta-delta coefficients.
    summarise : bool
        Whether to summarise MFCCs by utterance. If True, returns mean and standard
        deviation of MFCCs for each utterance.

    Returns:
    --------
    features_vec : np.ndarray
        MFCCs for each frame in the audio file. If deltas is True, contains also 
        delta and delta-delta coefficients. If summarise is True, contains mean and
        standard deviation of MFCCs for each utterance. Shape is (n_frames, n_mfccs).
    """
    y, sr = librosa.load(audio_file, sr=None)  # load audio file

    # pre-emphasis filter
    y = librosa.effects.preemphasis(y, coef=premphasis)

    # compute frame length and overlap in samples
    n_fft = int(win_length * sr / 1000)
    hop_length = int(overlap * sr / 1000)

    # extract mfccs
    features_vec = librosa.feature.mfcc(
        y=y,
        sr=sr,
        n_mfcc=n_mfcc,
        n_mels=n_mels,
        n_fft=n_fft,
        hop_length=hop_length,
        window='hamming',
        lifter=lifter,
        fmin=fmin,
        fmax=fmax
    )

    # delta features
    if deltas:
        features_vec = _delta_delta(features_vec)

    # summarise by utterance
    if summarise:
        features_vec = _summarise_features(features_vec)

    return features_vec.T


# pitch helper
def _pitch(
    sound: parselmouth.Sound, time_step: float = 0.0, f0min: float = 75.0, f0max: float = 600.0,
    max_candidates: int = 15, silence_threshold: float = 0.03,
    voicing_threshold: float = 0.45, octave_cost: float = 0.01,
    octave_jump_cost: float = 0.35, voiced_unvoiced_cost: float = 0.14
) -> Tuple[float, ...]:
    """
    Extracts pitch features from audio file using cross-correlation method.

    Parameters:
    -----------
    sound : parselmouth.Sound
        Parselmouth sound object.
    time_step : float
        Time step in seconds (default=0.0 (=auto)).
    f0min : float
        Minimum pitch frequency in Hz.
    f0max : float
        Maximum pitch frequency in Hz.
    max_candidates : int
        Maximum number of candidates.
    silence_threshold : float
        Threshold for silence.
    voicing_threshold : float
        Threshold for voicing.
    octave_cost : float
        Cost for octave.
    octave_jump_cost : float
        Cost for octave jump.
    voiced_unvoiced_cost : float
        Cost for unvoiced.

    Returns:
    --------
    pitch_features : Tuple[float, ...]
        Pitch features for each frame in the audio file. Shape is (n_frames,).
        The extracted features are:
        - mean pitch
        - median pitch
        - minimum pitch
        - maximum pitch
        - standard deviation of pitch
    """
    pitch: parselmouth.Pitch = parselmouth.praat.call(
        sound, "To Pitch (cc)",
        time_step, f0min, max_candidates, True, silence_threshold,
        voicing_threshold, octave_cost, octave_jump_cost,
        voiced_unvoiced_cost, f0max
    )
    mean_pitch: float = parselmouth.praat.call(
        pitch, 'Get mean', 0, 0, 'Hertz')
    med_pitch: float = parselmouth.praat.call(
        pitch, 'Get quantile', 0, 0, 0.5, 'Hertz')
    min_pitch: float = parselmouth.praat.call(
        pitch, 'Get minimum', 0, 0, 'Hertz', 'Parabolic')
    max_pitch: float = parselmouth.praat.call(
        pitch, 'Get maximum', 0, 0, 'Hertz', 'Parabolic')
    std_pitch: float = parselmouth.praat.call(
        pitch, 'Get standard deviation', 0, 0, 'Hertz')
    return mean_pitch, med_pitch, min_pitch, max_pitch, std_pitch


# TODO: create function to extract spectral features
# picth, formants, hnr, jittter, shimmer, spectral entropy,
# energy, zero-crossing-rate, spectral bandwidth, spectral contrast,
# spectral roll-off, formant dispersion
def acoustic_features(
        audio_file: str,
        f0min: float = 75.0, f0max: float = 600.0,
) -> np.ndarray:
    """
    Extracts acoustic features from audio file.

    Parameters:
    -----------
    audio_file : str
        Path to audio file.
    f0min : float
        Minimum pitch frequency in Hz.
    f0max : float
        Maximum pitch frequency in Hz.


    Returns:
    --------
    features_vec : np.ndarray
        Acoustic features for each frame in the audio file. Shape is (n_features,).
        The extracted features are:
        - pitch (cross-correlation): mean, median, minimum, maximum, standard deviation
        - formants (burg)
        - formant dispersion (average)
        - hnr
        - jitter
        - shimmer
        - energy
        - spectral entropy
        - spectral bandwidth
        - spectral contrast
        - spectral roll-off
        - spectral centroid
        - zero-crossing-rate
    """
    # Load audio
    y: np.ndarray
    sr: int
    y, sr = librosa.load(audio_file, sr=None)
    sound: parselmouth.Sound = parselmouth.Sound(audio_file)

    # Pitch
    pitch_features: Tuple[float, ...] = _pitch(sound, f0min, f0max)

    # Formants and formant dispersion
    # formant = sound.to_formant_burg()

# TODO: create function to extract LPCCs and LPC residual