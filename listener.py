#!/usr/bin/python

# open a microphone in pyAudio and listen for taps

import pyaudio
import struct
import math

INITIAL_TAP_THRESHOLD = 0.010
FORMAT = pyaudio.paInt16 
SHORT_NORMALIZE = (1.0/32768.0)
CHANNELS = 2
RATE = 44100  
INPUT_BLOCK_TIME = 0.02
# number of intervals / levels
NUM_LEVELS = 10
# 10 second sampling time to readjust levels to average levels.
RUNNING_AVERAGE_TIME = .5
RUNNING_AVERAGE_COUNT = int(RUNNING_AVERAGE_TIME / INPUT_BLOCK_TIME)
INPUT_FRAMES_PER_BLOCK = int(RATE*INPUT_BLOCK_TIME)
# if we get this many noisy blocks in a row, increase the threshold
OVERSENSITIVE = 15.0/INPUT_BLOCK_TIME                    
# if we get this many quiet blocks in a row, decrease the threshold
UNDERSENSITIVE = 120.0/INPUT_BLOCK_TIME 
# if the noise was longer than this many blocks, it's not a 'tap'
MAX_TAP_BLOCKS = 0.15/INPUT_BLOCK_TIME

def get_rms( block ):
    # RMS amplitude is defined as the square root of the 
    # mean over time of the square of the amplitude.
    # so we need to convert this string of bytes into 
    # a string of 16-bit samples...

    # we will get one short out for each 
    # two chars in the string.
    count = len(block)/2
    format = "%dh"%(count)
    shorts = struct.unpack( format, block )

    # iterate over the block.
    sum_squares = 0.0
    for sample in shorts:
        # sample is a signed short in +/- 32768. 
        # normalize it to 1.0
        n = sample * SHORT_NORMALIZE
        sum_squares += n*n

    return math.sqrt( sum_squares / count )


class Intervals2(object):
    def __init__(self, nIntervals):
        self.Ranges = [ 0 for x in range(nIntervals+1)]
        self.nIntervals = nIntervals

    def calculate(self, min, max):
        intSize = float(max-min)/float(self.nIntervals)
        for i in range(self.nIntervals+1):
            self.Ranges[i] = min+(i*intSize)

    def classify(self, nValue):
        if (nValue < self.Ranges[0]):
            return 0;
        if (nValue > self.Ranges[self.nIntervals]):
            return self.nIntervals;
        for i in range(self.nIntervals):
            if (self.Ranges[i] <= nValue <= self.Ranges[i+1]):
                return i
#        print ("Classify:  ", nValue, self.Ranges)

        return -1




class Levels2(object):

    def __init__(self):
        self.min = 0
        self.max = 0
        self.runningMin = 0
        self.runningMax = 0
        self.samplesCount = 0  # have not sampled yet.
        self.intervals = Intervals2(NUM_LEVELS)
        self.firstPass = True

    def classify(self, nLevel):
        return self.intervals.classify(nLevel)
        
    def sampleLevels(self, nLevel):
        bRecalc = False
        if (self.firstPass):
#            print ("A: ", nLevel, " Levels: ", self)
            if (self.samplesCount == 0):
                self.min = nLevel
                self.max = nLevel
            if (nLevel < self.min):
                self.min = nLevel
                bRecalc = True
            if (nLevel > self.max):
                self.max = nLevel
                bRecalc = True
            self.runningMin = self.min
            self.runningMax = self.max
            if (self.samplesCount == RUNNING_AVERAGE_COUNT):
                self.firstPass = False

        if (not self.firstPass):
            if (self.samplesCount == RUNNING_AVERAGE_COUNT):
#                print ("A: ", nLevel, " Levels: ", self)
                self.samplesCount = 0
                self.min = self.runningMin
                self.max = self.runningMax
                bRecalc = True
                self.runningMin = nLevel
                self.runningMax = nLevel
            if (nLevel < self.runningMin):
                self.runningMin = nLevel
            if (nLevel > self.runningMax):
                self.runningMax = nLevel

        if (bRecalc):
            self.intervals.calculate(self.min, self.max)

        self.samplesCount += 1


    def __str__(self):
        return  "Foo"

    def __repr__(self):
        x = self.intervals
        return str(self.intervals.Ranges)







class TapTester(object):
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = self.open_mic_stream()
        self.tap_threshold = INITIAL_TAP_THRESHOLD
        self.noisycount = MAX_TAP_BLOCKS+1 
        self.quietcount = 0 
        self.errorcount = 0
        self.levels = Levels2()
        self.cyclecount = 0

    def stop(self):
        self.stream.close()

    def find_input_device(self):
        device_index = None            
        for i in range( self.pa.get_device_count() ):     
            devinfo = self.pa.get_device_info_by_index(i)   
            print( "Device %d: %s"%(i,devinfo["name"]) )

            for keyword in ["mic","input"]:
                if keyword in devinfo["name"].lower():
                    print( "Found an input: device %d - %s"%(i,devinfo["name"]) )
                    device_index = i
                    return device_index

        if device_index == None:
            print( "No preferred input found; using default input device." )

        return device_index

    def open_mic_stream( self ):
        device_index = self.find_input_device()

        stream = self.pa.open(   format = FORMAT,
                                 channels = CHANNELS,
                                 rate = RATE,
                                 input = True,
                                 input_device_index = device_index,
                                 frames_per_buffer = INPUT_FRAMES_PER_BLOCK)

        return stream

    def tapDetected(self):
        print "Tap!"

    def listen(self):
        try:
            block = self.stream.read(INPUT_FRAMES_PER_BLOCK)
        except IOError, e:
            # dammit. 
            self.errorcount += 1
            print( "(%d) Error recording: %s"%(self.errorcount,e) )
            self.noisycount = 1
            return

        amplitude = get_rms( block )

        self.levels.sampleLevels(amplitude)
        n = self.levels.classify(amplitude)

        print "EEEEEEEEEE"*(1+n)


if __name__ == "__main__":
    tt = TapTester()

    while (True):
        tt.listen()



#class Levels(object):
#    class Intervals(object):
#        def __init__(self):
#            self.Low = [0,0]
#            self.Medium = [0,0]
#            self.High = [0,0]
#
#        def calculate(self, min, max):
#            if (min==max):
#                return
#            self.Low = [min, (max-min)/3.0]
#            self.Medium = [self.Low[1], self.Low[1]*2]
#            self.High = [self.Medium[1], max]
#
#    def __init__(self):
#        self.min = 0
#        self.max = 0
#        self.runningMin = 0
#        self.runningMax = 0
#        self.samplesCount = 0  # have not sampled yet.
#        self.intervals = self.Intervals()
#        self.firstPass = True
#
#    def classify(self, nLevel):
#        
#        if self.intervals.Low[0] <= nLevel < self.intervals.Low[1]:
#            return 0
#        elif self.intervals.Medium[0] <= nLevel < self.intervals.Medium[1]:
#            return 1
#        elif self.intervals.High[0] <= nLevel < self.intervals.High[1]:
#            return 2
#        else:
#            return -1
#
#    def sampleLevels(self, nLevel):
#        bRecalc = False
#        if (self.firstPass):
#            print ("A: ", nLevel, " Levels: ", self)
#            if (self.samplesCount == 0):
#                self.min = nLevel
#                self.max = nLevel
#            if (nLevel < self.min):
#                self.min = nLevel
#                bRecalc = True
#            if (nLevel > self.max):
#                self.max = nLevel
#                bRecalc = True
#            self.runningMin = self.min
#            self.runningMax = self.max
#            if (self.samplesCount == RUNNING_AVERAGE_COUNT):
#                self.firstPass = False
#
#        if (not self.firstPass):
#            if (self.samplesCount == RUNNING_AVERAGE_COUNT):
#                print ("A: ", nLevel, " Levels: ", self)
#                self.samplesCount = 0
#                self.min = self.runningMin
#                self.max = self.runningMax
#                bRecalc = True
#                self.runningMin = nLevel
#                self.runningMax = nLevel
#            if (nLevel < self.runningMin):
#                self.runningMin = nLevel
#            if (nLevel > self.runningMax):
#                self.runningMax = nLevel
#
#        if (bRecalc):
#            self.intervals.calculate(self.min, self.max)
#
#        self.samplesCount += 1
#
#
#
#
#
#    def __str__(self):
#        return  "Foo"
#
#    def __repr__(self):
#        x = self.intervals
#        return "L (%.4f,%.4f)  M(%.4f, %.4f), H (%.4f, %.4f)" % (x.Low[0], x.Low[1], x.Medium[0], x.Medium[1], x.High[0], x.High[1])
