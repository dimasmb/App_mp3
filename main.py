# PyQt5 modules
from PyQt5 import QtWidgets

# Python modules
import sys

# Main window ui import
from mainwindow import MiMP3


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MiMP3()
    window.show()
    sys.exit(app.exec())
