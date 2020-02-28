import os
import sys
import queue
import shutil
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
    onGetInfoStarted = pyqtSignal()
    onGetInfoFinished = pyqtSignal()
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
        
        # Tools
        self.ffmpeg_path = os.path.join(os.getcwd(), "tools", "ffmpeg.exe")
        self.ffprobe_path = os.path.join(os.getcwd(), "tools", "ffprobe.exe")

        # Input files
        #self.intro_video_path = os.path.join(os.getcwd(), "input", "intro_enc.mp4")
        self.intro_video_path = os.path.join(os.getcwd(), "input", "intro.mov")
        self.outro_video_path = os.path.join(os.getcwd(), "input", "outro.mov")

        # Temporary files
        self.clip_encoded_path = os.path.join(os.getcwd(), "tmp", "clip_encoded.mov")

        # Output file
        self.output_path = os.path.join(os.getcwd(), "output", "final.mp4")

        # Clip info
        self.clip_duration = 0.0 # seconds

    '''
    Add all functions to be executed to the jobs queue, 
    then call the run_jobs function to execute all of them
    '''
    def start(self, videoPath):
        # Create folders if don't exists
        os.makedirs(os.path.dirname(self.clip_encoded_path), exist_ok=True) # Tmp folder
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True) # Output folder

        # Extract info (only duration) from the clip.
        # This function is not enqueued
        self.extract_info(videoPath)

        # Add tasks to the jobs queue

        # Convert clip to .mov format if necessary
        if Path(videoPath).suffix == ".mov":
            shutil.copyfile(videoPath, self.clip_encoded_path)
        else:
            self.jobs.put(partial(self.convert, videoPath))

        # Add the intro to the clip
        self.jobs.put(self.join)
        # Clean all temporary files
        self.jobs.put(self.remove_temp_files)
        
        # Run
        self.onJobStarted.emit()
        self.run_jobs()

    def extract_info(self, videoPath):
        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        
        self.process.finished.connect(self.run_jobs)
        self.process.errorOccurred.connect(self.log_error)

        try:
            self.process.start(self.ffprobe_path, ["-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", videoPath])
            self.process.waitForFinished()

            self.clip_duration = float(self.process.readAll())
        except:
            print(sys.exc_info())

    '''
    Convert the video in order to have the same properties as the intro
    '''
    def convert(self, videoPath):
        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)

        self.process.started.connect(self.onConvertStarted.emit)
        self.process.readyReadStandardOutput.connect(partial(self.parse_process_output, lambda: self.process.readAllStandardOutput()))
        self.process.finished.connect(self.onConvertFinished.emit)
        self.process.finished.connect(self.run_jobs)
        self.process.errorOccurred.connect(self.log_error)

        try:
            self.process.start(self.ffmpeg_path, ["-y", "-i", videoPath, "-ac", "2", "-acodec", "aac", "-vcodec", "qtrle", "-s", "1280x720", "-r", "30", "-b:v", "64k", "-minrate", "64k", "-maxrate", "64k", "-strict", "experimental", self.clip_encoded_path])
        except:
            print(sys.exc_info())

    '''
    Join the intro vide and the previously (convert) encoded video.
    '''
    def join(self):
        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)

        self.process.started.connect(self.onJoinStarted.emit)
        self.process.readyReadStandardOutput.connect(partial(self.parse_process_output, lambda: self.process.readAllStandardOutput()))
        self.process.finished.connect(self.onJoinFinished.emit)
        self.process.finished.connect(self.run_jobs)
        self.process.errorOccurred.connect(self.log_error)

        try:
            self.process.start(self.ffmpeg_path, ["-y", "-i", self.clip_encoded_path, "-i", self.intro_video_path, "-i", self.outro_video_path, "-filter_complex", "[1:v]setpts=PTS-3/TB[delay]; [1:v]scale2ref[1:v][0:v]; [0:v][delay]overlay=0:0[over]; [2:v]setpts=PTS+" + str(self.clip_duration - 2) + "/TB[outdelay]; [over][outdelay]overlay=0:0", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", self.output_path])
        except:
            print(sys.exc_info())

    '''
    Remove the temporary files
    '''
    def remove_temp_files(self):
        self.write_log("Borrando archivos temporales...")

        # Remove all tmp files
        #for f in [self.clip_encoded_path, self.intro_joined_video_path, self.outro_joined_video_path]:
        path = Path(self.clip_encoded_path)
        if path.exists:
            self.write_log(f"Removing {path}...")
            path.unlink()

        self.write_log("Todos los arhivos temporales han sido borrados.")

        self.run_jobs()

    '''
    Open the Windows explorer on the path
    '''
    def open_explorer(self):
        if not self.output_path:
            self.onError.emit("No se ha encontrado el archivo.")
            return
            
        self.process =  QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)

        self.process.errorOccurred.connect(self.log_error)

        try: 
            self.process.start("explorer", [os.path.dirname(self.output_path)])
        except:
            print(sys.exc_info())
        

    # SLOTS
    '''
    This slot is connected to 'finished' signal from QProcess.
    This will execute the next function in the self.jobs queue.
    '''
    @QtCore.pyqtSlot()
    def run_jobs(self):
        if self.jobs.empty():
            self.onJobFinished.emit()
        else:
            self.jobs.get()()

    '''
    Convert the bytearray output from process to text
    '''
    @QtCore.pyqtSlot(FunctionType)
    def parse_process_output(self, funct):
        output = bytearray(funct())
        output = output.decode("utf-8")
        output = output[18:]
        output = "cp" + output
        
        self.write_log(output)

    '''
    Emit the signal to write the message on log (GUI textbox)
    '''
    @QtCore.pyqtSlot(str)
    def write_log(self, message):
        self.onLog.emit(message)

    '''
    Emit the message error when the process failed
    '''
    @QtCore.pyqtSlot(QtCore.QProcess.ProcessError)
    def log_error(self, value):
        message = f"ERROR: {self.processErrors[value]}"
        self.onError.emit(message)
