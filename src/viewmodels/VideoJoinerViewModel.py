import os
import sys
import queue
from pathlib import Path
from functools import partial
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from types import FunctionType

# TODO: Change all os.path by Path


class VideoJoinerViewModel(QtCore.QObject):
    # Signals
    onLog = pyqtSignal(str)
    onJobStarted = pyqtSignal()
    onJobFinished = pyqtSignal()
    onConvertStarted = pyqtSignal()
    onConvertFinished = pyqtSignal()
    onJoinStarted = pyqtSignal()
    onJoinFinished = pyqtSignal()
    onError = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # Contains all functions to be run
        self.jobs = queue.Queue()

        # List of process errors: https://doc.qt.io/qt-5/qprocess.html#ProcessError-enum
        self.processErrors = ["Failed to start", "Crashed", "Timeout", "Write error", "Read error", "Unknown error"]
        
        self.ffmpeg_path = os.path.join(os.getcwd(), 'tools', 'ffmpeg.exe')
        self.intro_video_path = os.path.join(os.getcwd(), "input", "intro_enc.mp4")
        self.clip_encoded_path = os.path.join(os.getcwd(), "output", "clip_enc.mp4")
        self.output_path = os.path.join(os.getcwd(), "output", "final.mp4")

    '''
    Add all functions to be executed to the jobs queue, 
    then call the runJobs function to execute all of them
    '''
    def start(self, videoPath):
        # Add task to the jobs queue
        self.jobs.put(partial(self.convert, videoPath))
        self.jobs.put(self.join)
        self.jobs.put(self.removeTempFiles)

        # Run
        self.onJobStarted.emit()
        self.runJobs()

    '''
    Convert the video in order to have the same properties as the intro
    '''
    def convert(self, videoPath):
        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)

        self.process.started.connect(self.onConvertStarted.emit)
        self.process.readyReadStandardOutput.connect(partial(self.parseProcessOutput, lambda: self.process.readAllStandardOutput()))
        self.process.finished.connect(self.onConvertFinished.emit)
        self.process.finished.connect(self.runJobs)
        self.process.errorOccurred.connect(self.logError)

        try:
            self.process.start(self.ffmpeg_path, ["-y", "-i", videoPath, "-acodec", "aac", "-vcodec", "libx264", "-s", "1920x1080", "-r", "60", "-strict", "experimental", self.clip_encoded_path]) 
        except:
            print(sys.exc_info())

    '''
    Join the intro vide and the previously (convert) encoded video.
    '''
    def join(self):
        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)

        self.process.started.connect(self.onJoinStarted.emit)
        self.process.readyReadStandardOutput.connect(partial(self.parseProcessOutput, lambda: self.process.readAllStandardOutput()))
        self.process.finished.connect(self.onJoinFinished.emit)
        self.process.finished.connect(self.runJobs)
        self.process.errorOccurred.connect(self.logError)

        try:
            self.process.start(self.ffmpeg_path, ["-y", "-i", self.intro_video_path, "-i", self.clip_encoded_path, "-f", "lavfi", "-t", "0.1", "-i", "anullsrc", "-filter_complex", "[0:v:0][2:a][1:v:0][2:a] concat=n=2:v=1:a=1 [v][a]", "-map", "[v]", "-map", "[a]", self.output_path])
        except:
            print(sys.exc_info())

    '''
    Remove the temporary files
    '''
    def removeTempFiles(self):
        self.writeLog("Removing temporary files...")
        # Remove clip encoded
        path = Path(self.clip_encoded_path)
        if path.exists():
            self.writeLog(f"Removing {path}...")
            path.unlink()

        self.writeLog("All temporary files has been removed")

    '''
    Open the Windows explorer on the path
    '''
    def openExplorer(self):
        if not self.output_path:
            self.onError.emit("Output file not found")
            return
            
        self.process =  QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)

        self.process.errorOccurred.connect(self.logError)

        try: 
            self.process.start("explorer", [os.path.dirname(self.output_path)])
        except:
            print(sys.exc_info())
        

    # SLOTS
    '''
    This is slot is connected to 'finished' signal from QProcess.
    This will execute the next function in the self.jobs queue.
    '''
    @QtCore.pyqtSlot()
    def runJobs(self):
        if self.jobs.empty():
            self.onJobFinished.emit()
        else:
            self.jobs.get()()

    '''
    Convert the bytearray output from process to text
    '''
    @QtCore.pyqtSlot(FunctionType)
    def parseProcessOutput(self, funct):
        output = bytearray(funct())
        output = output.decode("ascii")
        output = output[18:]
        output = "cp" + output
        
        self.writeLog(output)

    '''
    Emit the signal to write the message on log (GUI textbox)
    '''
    @QtCore.pyqtSlot(str)
    def writeLog(self, message):
        self.onLog.emit(message)

    '''
    Emit the message error when the process failed
    '''
    @QtCore.pyqtSlot(QtCore.QProcess.ProcessError)
    def logError(self, value):
        message = f"ERROR: {self.processErrors[value]}"
        self.onError.emit(message)
