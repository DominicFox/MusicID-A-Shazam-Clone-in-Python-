import pyaudio
import wave
import numpy
from sys import getsizeof
#import matplotlib.pyplot as plt
import cmath
import numpy.fft as fft
from profilehooks import profile
from scipy.signal import butter, lfilter, freqz, fftconvolve, resample_poly
import pickle
from timeit import default_timer as timer
import os


def nextPowerOf2(x): # Find the next power of two after x
    return 1<<(x-1).bit_length()

def MergeSort(array): # Sort a list using the 'merge sort' implementation. Did not need to write this myself, but I wanted to.
    if len(array) == 1:
        return array
    
    a = array[:len(array)//2]
    b = array[len(array)//2:]

    a = MergeSort(a)
    b = MergeSort(b)

    c = []
    while len(a) and len(b) != 0:
        if a[0] > b[0]: # < to sort in ascending order. > to sort in descending order
            c.append(a[0])
            del a[0]
        else:
            c.append(b[0])
            del b[0]

    if len(a) == 0:
        for i in range(0, len(b)):
            c.append(b[i])
    else:
        for i in range(0, len(a)):
            c.append(a[i])

    return c

def FramesToSeconds(frames, sampleRate): # Convert a number of samples into the amount of time they represent
    seconds = frames / sampleRate
    return seconds

def HammingWindow(N): # Create the mathematical function representing the Hamming Window Function
    n = numpy.arange(0, N-1, 1)
    y = (0.54-0.46*numpy.cos((2*cmath.pi*n)/(N-1)))  
    return y  

def FastFourierTransform(x, N): # Recursively compute the Fourier Transform of the audio signal
    # N MUST be a power of 2 else the function will crash. Code ensures this condition is true.
    if N==1:
        return x 
    else:
        evenIndexDFT=FastFourierTransform(x[::2], int(N/2)) #Recurse over the even index list
        oddIndexDFT=FastFourierTransform(x[1::2], int(N/2)) #Recurse over the odd index list
        firstHalfFFT=[]
        secondHalfFFT=[]
        for k in range (0, int(N/2)): #Combine odd and even FFT to form complete FFT of input data
            firstHalfFFT.append(evenIndexDFT[k] + cmath.exp((-2j*cmath.pi*k)/N) * oddIndexDFT[k])
            secondHalfFFT.append(evenIndexDFT[k] - cmath.exp((-2j*cmath.pi*k)/N) * oddIndexDFT[k])
    return firstHalfFFT + secondHalfFFT

def LowPassFilter(cutoff, transitionBand, Fs): # Create a low pass filter for the audio. ie only let through frequencies under a certain threshold
    # NOTE: I DID NOT WRITE THIS FUNCTION
    cutoff = cutoff/Fs
    N = int(numpy.ceil((4 / transitionBand)))
    if not N % 2: N += 1  # Make sure that N is odd.
    n = numpy.arange(N)

    # Compute a low-pass filter with cutoff frequency fH.
    lpf = numpy.sinc(2 * cutoff * (n - (N - 1) / 2.))
    lpf *= numpy.blackman(N)
    lpf = lpf / numpy.sum(lpf)
    return lpf

def Downsample(averagingChunk, data): # Downsample the audio to 11025Hz from 44100Hz
    downsampledData = [sum(data[i:i+averagingChunk])/averagingChunk for i in range(0, len(data), averagingChunk)]
    return downsampledData

def StereoToMono(stereoAudio): # Convert stereo audio to mono
    mono = stereoAudio.sum(axis=1) / 2
    return mono

def InitialiseAudio(filename, pointerInAudio): # Read in the audio from the wav file 
    sound = wave.open(filename, 'rb')

    # Establish some constants for the sound recording
    CHANNELS = sound.getnchannels()
    SAMPLERATE = sound.getframerate()
    FRAMES = sound.getnframes()
    DURATION =  FRAMES/SAMPLERATE
    CHUNK = 2048

    # Store the chunks in an array
    audioData = []
    for i in range(0, int((SAMPLERATE/CHUNK)*DURATION)):
        audioData.append(sound.readframes(CHUNK))

    # Join together the audio data into a 1D array, and convert byte values to integers
    concatData = b''.join(audioData[pointerInAudio:])
    return ((numpy.frombuffer(concatData, dtype = '<i2').reshape(-1, CHANNELS)), SAMPLERATE, DURATION, int((SAMPLERATE/CHUNK)*DURATION))

def ZeroPad(audio): # Add extra zeros to the end of some audio data to make the total number of samples be a power of 2
    zeroes = numpy.zeros((nextPowerOf2(len(audio))-len(audio),), dtype=numpy.int8)
    return list(audio) + list(zeroes)

def FilterFrequencies(audio, SAMPLERATE): # Apply the low pass filter to the audio
    lpf = LowPassFilter(5000, 0.0001, SAMPLERATE)
    return fftconvolve(audio, lpf)

def GenerateArrayOfWindowedData(windowSize, windowFunction, windowOverlap, downsampledAudio): # Apply the window function to audio and save each section of windowed audio to an array
    windowedData=[]
    zeroArray = numpy.array(numpy.zeros((len(downsampledAudio)-windowSize,), dtype=numpy.float16))
    for i in range(0, int(len(downsampledAudio)/windowSize + (len(downsampledAudio)/windowSize * (windowOverlap/100)))):
        index = (i * windowSize)-int(i*windowSize*(windowOverlap/100))
        tempWindowed = windowFunction * downsampledAudio[index:index+windowSize]
        windowedData.append(numpy.insert(zeroArray, index, tempWindowed))
    return windowedData

def FourierAcrossWindows(windowedAudio, windowSize): # Apply the fourier transform to each of the pieces of windowed data
    frequencyBin=[]
    for i in range (0, len(windowedAudio)):
        frequencyBin.append(numpy.abs(FastFourierTransform(windowedAudio[i][i*windowSize:i*windowSize+windowSize], windowSize)))
    return frequencyBin

def LocatePowerfulFrequencies(fullAudioArray): # Find the strongest frequencies from all those present in the audio
    # Sort the frequency bins for each fft result into X logarithmic bands
    frequencyBands = ([[fullAudioArray[j][0:10] if i == 0
                        else fullAudioArray[j][10:20] if i == 1 
                        else fullAudioArray[j][20:40] if i == 2
                        else fullAudioArray[j][40:80] if i == 3
                        else fullAudioArray[j][80:160] if i == 4
                        else fullAudioArray[j][160:250] if i == 5
                        else fullAudioArray[j][250:350] if i == 6
                        else fullAudioArray[j][350:512]
                        for i in range(0, 8)] 
                        for j in range(0, len(fullAudioArray))])

    # For each band locate and store the strongest bin of frequencies
    strongestBinPerBand = [[MergeSort(frequencyBands[j][i])[0] for i in range(3, len(frequencyBands[j]))] for j in range(0, len(frequencyBands))]

    # Calculate the average value of these 6 powerful bins, for each element in the frequency band array
    avBinValue = sum(sum(numpy.array(strongestBinPerBand[:][:])))/(len(strongestBinPerBand[:][:])*6)

    # Now keep the bins from the six powerful ones (per FFT output) that are above this mean value (multiplied by a coefficient, A)
    A = 0.3
    powerfulFrequencyBins = [[strongestBinPerBand[j][i] for i in range(0, len(strongestBinPerBand[j])) if strongestBinPerBand[j][i][0] > A*avBinValue[0]] for j in range(0, len(strongestBinPerBand))]
    
    return powerfulFrequencyBins

def WriteFingerprintToTextFile(timeData, freqData, num, writeType): # Write the audio fingerprint out to a text file
    if writeType == 'w':
        fingerprintText = open(os.path.join(os.getcwd(), "SampleFingerprint.txt"), 'w+')
    elif writeType == 'a':
        fingerprintText = open(os.path.join(os.getcwd(), "SampleFingerprint.txt"), 'a+')
    for i in range(0,len(timeData)):
            fingerprintText.write(str(timeData[i]) + ' ' + str(freqData[i]) + '\n')
    fingerprintText.close

def SeparateAndFlattenAudioData(powerfulFrequencies): # Expand amplitude, time and frequency data to three different arrays and also convert them to be 1D arrays
    # Separate the data into three arrays
    ampData = [[powerfulFrequencies[i][j][0] for j in range(0, len(powerfulFrequencies[i]))] for i in range(0, len(powerfulFrequencies))]
    timeData = [[powerfulFrequencies[i][j][1] for j in range(0, len(powerfulFrequencies[i]))] for i in range(0, len(powerfulFrequencies))]
    freqData = [[powerfulFrequencies[i][j][2] for j in range(0, len(powerfulFrequencies[i]))] for i in range(0, len(powerfulFrequencies))]

    # Flatten the data to be 1D
    ampFlatten = [y for x in ampData for y in x]
    timeFlatten = [y for x in timeData for y in x]
    freqFlatten = [y for x in freqData for y in x]

    return ampFlatten, timeFlatten, freqFlatten

def PlotConstellationMapAndSpectrogram(timeData, freqData, duration, audio, windowSize, samplerate): # Use Matplotlib to graphically plot the spectrogram and filtered spectrogram
    plt.figure(1)
    plt.subplot(211)
    plt.scatter(x=timeData, y=freqData, marker='.', linewidths=0.5)
    plt.xlim(0, duration)
    plt.ylim(0, 5000)

    # Plot spectrogram of downsampled audio
    plt.subplot(212)
    Pxx, freqs, bins, im = plt.specgram(audio, NFFT=windowSize, Fs=samplerate)
    cbar = plt.colorbar(im)
    plt.xlabel('Time (s)')
    plt.ylabel('Frequency (Hz)')
    cbar.set_label('Intensity (dB)')
    plt.ylim(0,5000)
    plt.show()

def GenerateConstellationMap(filename, songNumber, pointerInAudio): # Load a WAV file and then generate a constellation map
    audioData, SAMPLERATE, DURATION, pointer = InitialiseAudio(filename, pointerInAudio)
    
    # Convert stereo to mono 
    monoAudio = StereoToMono(audioData)
    
    # Pad the audio with zeroes until there are a power of two number of items in the array
    zeroPaddedAudio = ZeroPad(monoAudio)

    # Filter out frequencies above 5000 Hz to avoid aliasing before downsampling 
    filteredAudio = FilterFrequencies(zeroPaddedAudio, SAMPLERATE)

    # Downsample the signal to 10k samples/sec
    downsampledAudio = Downsample(4, filteredAudio)
    # downsampledAudio = resample_poly(filteredAudio, 1, 4)
    SAMPLERATE = SAMPLERATE/4

    #Create hamming window
    windowSize = 1024
    hammingWindow = numpy.array(HammingWindow(windowSize+1))
    
    # Loop through the audio data and bounce the window through the audio. Apply the fourier transform to the whole audio each time the window hops to a new position           
    windowOverlap = 0 #percent
    windowedAudio = GenerateArrayOfWindowedData(windowSize, hammingWindow, windowOverlap, downsampledAudio)

    # Generate frequency bins for every 1024 samples of audio, and also store the time associated with each bin of frequencies
    frequencyResolution = SAMPLERATE/windowSize
    audioFrequencyDomain = FourierAcrossWindows(windowedAudio, windowSize)
    audioFrequencyDomain = [[[audioFrequencyDomain[i][j], FramesToSeconds(i*windowSize, SAMPLERATE)+((FramesToSeconds(windowSize, SAMPLERATE)/windowSize)*j) + FramesToSeconds(pointerInAudio*2048, 44100), j*frequencyResolution] for j in range(0,int(len(audioFrequencyDomain[i])/2))] for i in range(0,len(audioFrequencyDomain))] 

    # Find the most powerful frequencies in the current audio
    powerfulFrequencies = LocatePowerfulFrequencies(audioFrequencyDomain)

    # Plot constellation map of the filtered spectrogram
    ampData, timeData, freqData = SeparateAndFlattenAudioData(powerfulFrequencies)
    #PlotConstellationMapAndSpectrogram(timeData, freqData, DURATION, downsampledAudio, windowSize, SAMPLERATE)

    # Copy out the current fingerprint to a text file
    if pointerInAudio == 0:
        writeType = 'w'
    else:
        writeType = 'a'
    WriteFingerprintToTextFile(timeData, freqData, songNumber, writeType)

    return pointer


def RecordAudio(recordingDuration, OUTPUT_FILENAME, saveFrequency): # Record audio for a specified amount of time and write it to a wav file
    CHANNELS = 1
    SAMPLERATE = 44100
    FORMAT = pyaudio.paInt16
    CHUNK = 1024

    py = pyaudio.PyAudio()

    stream = py.open(channels = CHANNELS, rate = SAMPLERATE, format = FORMAT, frames_per_buffer = CHUNK, input = True, output = True)
    saveFile = wave.open(OUTPUT_FILENAME, 'wb')
    saveFile.setframerate(SAMPLERATE)
    saveFile.setnchannels(CHANNELS)
    saveFile.setsampwidth(py.get_sample_size(FORMAT))

    global stopCondition
    stopCondition = False
    frames = []
    i = 0
    while (i <= recordingDuration*43) and stopCondition == False:
        i=i+1
        audioBuffer = stream.read(CHUNK, exception_on_overflow = False)
        frames.append(audioBuffer)
        if i % (int(43*saveFrequency)) == 0:  #saveFrequency is in seconds
            saveFile.writeframes(b''.join(frames))
            frames.clear()

    py.terminate()
    stream.stop_stream()
    stream.close()

    saveFile.close()
