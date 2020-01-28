import sys

from PyQt5.QtWidgets import QApplication

from src.views.VideoJoinerView import Ui_MainWindow, VideoJoinerView
from src.viewmodels.VideoJoinerViewModel import VideoJoinerViewModel

def main():
    app = QApplication(sys.argv)

    viewmodel = VideoJoinerViewModel()

    gui = Ui_MainWindow()
    view = VideoJoinerView(gui, viewmodel = viewmodel)
    
    view.show()

    # Execute main loop
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
