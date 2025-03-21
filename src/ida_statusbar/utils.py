from PyQt5.QtWidgets import qApp, QMainWindow


def findMainWindow():
    for widget in qApp.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            return widget
    return None