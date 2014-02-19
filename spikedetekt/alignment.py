'''
Routines for aligning and interpolating waves extracted after thresholding.
'''
import numpy as np
from scipy.signal import cspline1d, cspline1d_eval
from scipy.interpolate import interp1d
from utils import get_padded
from parameters import Parameters, GlobalVariables
from log import log_warning


def extract_wave(IndList, FilteredArr, s_before,
                 s_after, n_ch, s_start, Threshold):
    '''
    Extract an aligned wave corresponding to a spike.

    Arguments:

    IndList
        A list of pairs (sample_number, channel_number) returned from the
        thresholding and flood filling algorithm
    FilteredArr
        An array of shape (numsamples, numchannels) containing the filtered
        wave data
    s_before, s_after
        The number of samples to return before and after the peak

    Returns a tuple (Wave, PeakSample, ST):

    Wave
        The wave aligned around the peak (with interpolation to give subsample
        alignment), consisting of s_before+s_after+1 samples.
    PeakSample
        The index of the peak sample in FilteredArr (the peak sample in Wave
        will always be s_before).
    ChMask
        The mask for this spike, a boolean array of length the number of
        channels, with value 1 if the channel is used and 0 otherwise.
    '''
    if Parameters['USE_WEIGHTED_MEAN_PEAK_SAMPLE'] or Parameters['UPSAMPLING_FACTOR'] > 1:
        return extract_wave_new(IndList, FilteredArr,
                                s_before, s_after, n_ch, s_start, Threshold)
    IndArr = np.array(IndList, dtype=np.int32)
    SampArr = IndArr[:, 0]
    log_fd = GlobalVariables['log_fd']
    if np.amax(SampArr) - np.amin(SampArr) > Parameters['CHUNK_OVERLAP'] / 2:
        s = '''
        ************ ERROR **********************************************
        Connected component found with width larger than CHUNK_OVERLAP/2.
        Spikes could be repeatedly detected, increase the size of
        CHUNK_OVERLAP and re-run.
        Component sample range: {sample_range}
        *****************************************************************
        '''.format(sample_range=(s_start + np.amin(SampArr),
                                 s_start + np.amax(SampArr)))
        log_warning(s, multiline=True)
        # exit()
    ChArr = IndArr[:, 1]
    n_ch = FilteredArr.shape[1]

    # Find peak sample and channel
    # TODO: argmin only works for negative threshold crossings
    PeakInd = FilteredArr[SampArr, ChArr].argmin()
    PeakSample, PeakChannel = SampArr[PeakInd], ChArr[PeakInd]

    # Ensure that we get a fixed size chunk of the wave, padded with zeroes if
    # the segment from PeakSample-s_before-1 to PeakSample+s_after+1 goes
    # outside the bounds of FilteredArr.
    WavePlus = get_padded(FilteredArr,
                          PeakSample - s_before - 1, PeakSample + s_after + 1)
    # Perform interpolation around the fractional peak
    Wave = interp_around_peak(WavePlus, s_before + 1,
                              PeakChannel, s_before, s_after)
    # Return the aligned wave, the peak sample index and the associated mask
    # which is computed by counting the number of times each channel index
    # appears in IndList and then converting to a bool (so that channel i is
    # True if channel i features at least once).
    bc = np.bincount(ChArr)
    # convert to bool and force it to have the right type
    ChMask = np.zeros(n_ch, dtype=np.bool8)
    ChMask[:len(bc)] = bc.astype(np.bool8)

    return Wave, PeakSample, ChMask


def abc(x_3, y_3):
    M = np.vstack((x_3 ** 2, x_3, np.ones_like(x_3)))
    return np.linalg.solve(M.T, y_3)


def max_t(a_b_c):
    return -a_b_c[1] / (2 * a_b_c[0])


def interp_around(X_sc, s_fracpeak, s_before, s_after):
    n_c = X_sc.shape[1]
    n_s = s_before + s_after
    old_s = np.arange(X_sc.shape[0])
    new_s = np.arange(
        s_fracpeak -
        s_before,
        s_fracpeak +
        s_after,
        dtype=np.float32)
    f = interp1d(old_s, X_sc, bounds_error=True, kind='cubic', axis=0)
    return f(new_s)


def interp_around_peak(X_sc, i_intpeak, c_peak, s_before, s_after):
    # Presumably this finds the coefficients a, b, c for ax^2+bx+c to fit a
    # quadratic to the three points surrounding the peak
    a_b_c = abc(np.arange(i_intpeak - 1, i_intpeak + 2, dtype=np.float32),
                X_sc[i_intpeak - 1:i_intpeak + 2, c_peak])
    # and this then finds the fractional sample of the peak, using the fitted
    # quadratic, which is a little odd given that we then use cubic
    # interpolation afterwards, but it's probably not too bad for high sample
    # rates.
    s_fracpeak = max_t(a_b_c)
    return interp_around(X_sc, s_fracpeak, s_before, s_after)


def extract_wave_new(IndList, FilteredArr, s_before,
                     s_after, n_ch, s_start, Threshold):
    IndArr = np.array(IndList, dtype=np.int32)
    SampArr = IndArr[:, 0]
    ChArr = IndArr[:, 1]
    n_ch = FilteredArr.shape[1]
    log_fd = GlobalVariables['log_fd']
    if np.amax(SampArr) - np.amin(SampArr) > Parameters['CHUNK_OVERLAP'] / 2:
        s = '''
        ************ ERROR **********************************************
        Connected component found with width larger than CHUNK_OVERLAP/2.
        Spikes could be repeatedly detected, increase the size of
        CHUNK_OVERLAP and re-run.
        Component sample range: {sample_range}
        *****************************************************************
        '''.format(sample_range=(s_start + np.amin(SampArr),
                                 s_start + np.amax(SampArr)))
        log_warning(s, multiline=True)
        # exit()

    bc = np.bincount(ChArr)
    # convert to bool and force it to have the right type
    ChMask = np.zeros(n_ch, dtype=np.bool8)
    ChMask[:len(bc)] = bc.astype(np.bool8)

    # Find peak sample:
    # 1. upsample channels we're using on thresholded range
    # 2. find weighted mean peak sample
    SampArrMin, SampArrMax = np.amin(SampArr) - 3, np.amax(SampArr) + 4
    # print ' SampArrMin = ', SampArrMin,' SampArrMax = ', SampArrMax, '\n'
    WavePlus = get_padded(FilteredArr, SampArrMin, SampArrMax)
    WavePlus = WavePlus[:, ChMask]
    # upsample WavePlus
    upsampling_factor = Parameters['UPSAMPLING_FACTOR']
    if upsampling_factor > 1:
        old_s = np.arange(WavePlus.shape[0])
        new_s_i = np.arange((WavePlus.shape[0] - 1) * upsampling_factor + 1)
        new_s = np.array(new_s_i * (1.0 / upsampling_factor), dtype=np.float32)
        f = interp1d(old_s, WavePlus, bounds_error=True, kind='cubic', axis=0)
        UpsampledWavePlus = f(new_s)
    else:
        UpsampledWavePlus = WavePlus
    # find weighted mean peak for each channel above threshold
    if Parameters['USE_WEIGHTED_MEAN_PEAK_SAMPLE']:
        peak_sum = 0.0
        total_weight = 0.0
        for ch in xrange(WavePlus.shape[1]):
            X = UpsampledWavePlus[:, ch]
            if Parameters['DETECT_POSITIVE']:
                X = -np.abs(X)
            i_intpeak = np.argmin(X)
            left, right = i_intpeak - 1, i_intpeak + 2
            if right > len(X):
                left, right = left + len(X) - right, len(X)
            elif left < 0:
                left, right = 0, right - left
            a_b_c = abc(np.arange(left, right, dtype=np.float32),
                        X[left:right])
            s_fracpeak = max_t(a_b_c)
            if Parameters['USE_SINGLE_THRESHOLD']:
                weight = -(X[i_intpeak] + Threshold)
            else:
                weight = -(X[i_intpeak] + Threshold[ch])
            if weight < 0:
                weight = 0
            peak_sum += s_fracpeak * weight
            total_weight += weight
        s_fracpeak = (peak_sum / total_weight)
    else:
        if Parameters['DETECT_POSITIVE']:
            X = -np.abs(UpsampledWavePlus)
        else:
            X = UpsampledWavePlus
        s_fracpeak = 1.0 * np.argmin(np.amin(X, axis=1))
    # s_fracpeak currently in coords of UpsampledWavePlus
    s_fracpeak = s_fracpeak / upsampling_factor
    # s_fracpeak now in coordinates of WavePlus
    s_fracpeak += SampArrMin
    # s_fracpeak now in coordinates of FilteredArr

    # get block of given size around peaksample
    try:
        s_peak = int(s_fracpeak)
    except ValueError:
        # This is a bit of a hack. Essentially, the problem here is that
        # s_fracpeak is a nan because the interpolation didn't work, and
        # therefore we want to skip the spike. There's already code in
        # core.extract_spikes that does this if a LinAlgError is raised,
        # so we just use that to skip this spike (and write a message to the
        # log).
        raise np.linalg.LinAlgError
    WaveBlock = get_padded(FilteredArr,
                           s_peak - s_before - 1, s_peak + s_after + 2)

    # Perform interpolation around the fractional peak
    old_s = np.arange(s_peak - s_before - 1, s_peak + s_after + 2)
    new_s = np.arange(
        s_peak - s_before,
        s_peak + s_after) + (s_fracpeak - s_peak)
    f = interp1d(old_s, WaveBlock, bounds_error=True, kind='cubic', axis=0)
    Wave = f(new_s)

    return Wave, s_peak, ChMask
