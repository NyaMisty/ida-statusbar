import logging
from typing import Any
import idaapi
from dataclasses import dataclass
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import QTimer
logger = logging.getLogger(__name__)

@dataclass
class WidgetItem:
    widget: QWidget
    widgetTag: str | None
    widgetUpdateFunc: Any | None

class StatusWidgetContainer(QWidget):
    def __init__(self):
        super(StatusWidgetContainer, self).__init__()
        self.installed = False
        self.setLayout(QHBoxLayout())
        # self.layout().setSpacing(0)
        self.layout().setContentsMargins(0,0,0,0)
        self.widgets: list[WidgetItem] = []
        self.timer = QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self._update)

    def _update(self):
        # logger.info("_update() triggered")
        for item in self.widgets:
            if item.widgetUpdateFunc is not None:
                item.widgetUpdateFunc()
        return 1.0
    
    def addWidget(self, widget, widgetTag=None, widgetUpdateFunc=None):
        """
        Add a QWidget to status bar
        """
        logger.info("Adding widget %s (with tag %s)", widget, widgetTag)
        item = WidgetItem(widget, widgetTag, widgetUpdateFunc)
        self.widgets.append(item)
        self.layout().addWidget(widget)
        return item
    
    def findWidgetByTag(self, widgetTag):
        """
        Find an added widget by tag
        """
        for item in list(self.widgets):
            if item.widgetTag == widgetTag:
                yield item

    def removeWidgetByTag(self, tag: str):
        """
        Remove widget from status bar by tag
        """
        logger.debug("Removing all widgets with tag %s", tag)
        for item in self.findWidgetByTag(tag):
            self.widgets.remove(item)
            self.layout().removeWidget(item.widget)
    
    def removeWidget(self, widget):
        """
        Remove widget from status bar
        """
        logger.debug("Removing widget %s", widget)
        for item in list(self.widgets):
            if widget is item.widget:
                self.widgets.remove(item)
        self.layout().removeWidget(widget)

    def listWidgets(self):
        """
        Returns all currently registered status bar widget
        """
        return list(self.widgets)

    def showText(self, tag: str, text: str, func: Any=None):
        """
        Show a simple text widget (QLabel) in the status bar.
        
        The text control will be identified by `tag`, which can be used to update / remove the text
        
        returns the inner QLabel widget
        """
        currentWidgets = list(self.findWidgetByTag(tag))
        if currentWidgets:
            if len(currentWidgets) != 1 or not isinstance(currentWidgets[0].widget, QLabel):
                raise Exception("showText can only be used for simple widget, however there's already %d widgets: %s", len(currentWidgets), currentWidgets)
            currentWidget = currentWidgets[0]
            label = currentWidget.widget
        else:
            label = QLabel()
            currentWidget = self.addWidget(label, tag, func)
        currentWidget.widgetUpdateFunc = func
        label.setText(text)
        return label

    def showTextByFunc(self, tag, func):
        """
        Show a simple text widget (QLabel), like `showText`, but its content is automatically updated by calling `func` every 500ms
        """
        def updater():
            self.showText(tag, func(), updater)
        self.showText(tag, func(), updater)
        self._update()

    def removeText(self, tag):
        """
        Helper function to remove the widget shown by showText()
        """
        self.removeWidgetByTag(tag)
    
    def install(self, window) -> None:
        assert not self.installed
        logger.debug("Installing the status bar widget")
        window.statusBar().addPermanentWidget(self)
        self.installed = True
        self.timer.start()

    def uninstall(self, window):
        assert self.installed
        logger.debug("Uninstalling the status bar widget")
        window.statusBar().removePermanentWidget(self)
        self.installed = False
        self.timer.stop()

StatusWidgetContainerInstance: StatusWidgetContainer | None = None
def getStatusBar() -> StatusWidgetContainer:
    """
    Get stautus bar class
    """
    global StatusWidgetContainerInstance
    if not StatusWidgetContainerInstance:
        StatusWidgetContainerInstance = StatusWidgetContainer()
        if idaapi.is_idaq() and not idaapi.cvar.batch:
            from .utils import findMainWindow
            _window = findMainWindow()
            if not _window:
                logger.info("cannot find main window currently, trying to install status bar later...")
                class timercallback_t(object):
                    def __init__(self):
                        self.interval = 1000
                        self.obj = idaapi.register_timer(self.interval, self)
                        if self.obj is None:
                            raise RuntimeError("Failed to register timer")

                    def __call__(self):
                        _window = findMainWindow()
                        if _window:
                            StatusWidgetContainerInstance.install(_window)
                            # Unregister the timer when main window is found
                            return -1
                        return self.interval

                timercallback_t()
            else:
                StatusWidgetContainerInstance.install(_window)
        else:
            logger.info("IDA is running in terminal mode or batch mode, not showing status bar!")
            
    return StatusWidgetContainerInstance