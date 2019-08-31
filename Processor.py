#! /usr/bin/env python3.4
import sys
from PySide.QtGui import *
from SteganographyGUI import *
from functools import partial
from scipy import misc
from PIL import Image, ImageQt
from Steganography import *

class Processor(QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        super(Processor, self).__init__(parent)
        self.setupUi(self)
        self.payload1 = None
        self.payload2 = None
        self.carrier1 = None
        self.carrier2 = None
        self.carrier2path = None

        self.chkApplyCompression.stateChanged.connect(self.setCompression)
        self.slideCompression.valueChanged.connect(self.slideChange)
        self.chkOverride.stateChanged.connect(self.saveValid)
        self.btnSave.clicked.connect(self.saveEmbedded)
        self.btnExtract.clicked.connect(self.extractEmbedded)
        self.btnClean.clicked.connect(self.cleanImg)

        self.viewPayload1.acceptDrops()
        self.viewPayload1.dragEnterEvent = partial(self.dragEnterEvent)
        self.viewPayload1.dropEvent = partial(self.dropView, self.viewPayload1)
        self.viewCarrier1.acceptDrops()
        self.viewCarrier1.dragEnterEvent = partial(self.dragEnterEvent)
        self.viewCarrier1.dropEvent = partial(self.dropView, self.viewCarrier1)
        self.viewCarrier2.acceptDrops()
        self.viewCarrier2.dragEnterEvent = partial(self.dragEnterEvent)
        self.viewCarrier2.dropEvent = partial(self.dropView, self.viewCarrier2)

    def cleanImg(self):
        image = self.carrier2.clean()
        misc.imsave(self.carrier2path, image, 'png')
        scene = QGraphicsScene()
        pixmap = QPixmap(self.carrier2path)
        scene.addPixmap(pixmap)
        scene.dragMoveEvent = partial(self.dragMoveEvent)
        self.viewCarrier2.setScene(scene)
        self.viewCarrier2.fitInView(scene.sceneRect(), QtCore.Qt.KeepAspectRatio)
        self.viewCarrier2.show()
        self.lblCarrierEmpty.setText('>>>> Carrier Empty <<<<')
        self.btnClean.setEnabled(False)
        self.btnExtract.setEnabled(False)
        if (self.viewPayload2.scene()):
            scene = self.viewPayload2.scene().clear()
            self.viewPayload2.setScene(scene)

    def extractEmbedded(self):
        image = self.carrier2.extractPayload()
        try:
            image = Image.fromarray(image.rawData)
        except:
            return
        imageQt = QImage(ImageQt.ImageQt(image))
        pixmap = QPixmap.fromImage(imageQt)
        scene = QGraphicsScene()
        scene.addPixmap(pixmap)
        scene.dragMoveEvent = partial(self.dragMoveEvent)
        self.viewPayload2.setScene(scene)
        self.viewPayload2.fitInView(scene.sceneRect(), QtCore.Qt.KeepAspectRatio)
        self.viewPayload2.show()


    def saveEmbedded(self):
        filePath, _ = QFileDialog.getSaveFileName(self, caption='Save Embedded Image ...')

        if not filePath:
            return

        if (not filePath.endswith('.png')):
            filePath += '.png'

        embedded = self.carrier1.embedPayload(payload=self.payload1, override=self.chkOverride.isChecked())
        misc.imsave(filePath, embedded, 'png')

    def saveValid(self):
        if (self.carrier1 is None or self.payload1 is None):
            self.btnSave.setEnabled(False)
            return
        if (self.lblPayloadFound.text() is not '' and not self.chkOverride.isChecked()):
            self.btnSave.setEnabled(False)
            return
        if (int(self.txtPayloadSize.text()) > int(self.txtCarrierSize.text())):
            self.btnSave.setEnabled(False)
            return
        self.btnSave.setEnabled(True)
        return

    def slideChange(self):
        self.txtCompression.setText(str(self.slideCompression.value()))
        if (self.payload1 is not None):
            self.payload1 = Payload(self.payload1.rawData, int(self.slideCompression.value()))
            self.txtPayloadSize.setText(str(len(self.payload1.json)))
            self.saveValid()

    def setCompression(self):
        if (self.chkApplyCompression.isChecked()):
            self.slideCompression.setEnabled(True)
            self.txtCompression.setEnabled(True)
            self.lblLevel.setEnabled(True)
            if (self.payload1 is not None):
                self.payload1 = Payload(self.payload1.rawData, int(self.slideCompression.value()))
                self.txtPayloadSize.setText(str(len(self.payload1.json)))
                self.saveValid()
        else:
            self.slideCompression.setEnabled(False)
            self.txtCompression.setEnabled(False)
            self.lblLevel.setEnabled(False)
            if (self.payload1 is not None):
                self.payload1 = Payload(self.payload1.rawData, -1)
                self.txtPayloadSize.setText(str(len(self.payload1.json)))
                self.saveValid()

    def dropView(self, view, event):
        if (event.mimeData().hasUrls):
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            fileName = str(event.mimeData().urls()[0].toLocalFile())
            if (fileName.endswith('.png')):
                self.loadView(view, fileName)
            else:
                event.ignore()
        else:
            event.ignore()

    def loadView(self, view, fileName):
        image = misc.imread(fileName)
        try:
            if ('Payload' in view.objectName()):
                value = Payload(image)
                self.chkApplyCompression.setChecked(False)
                self.slideCompression.setValue(0)
                self.txtCompression.setText('0')
            elif ('Carrier' in view.objectName()):
                value = Carrier(image)
        except:
            return
        scene = QGraphicsScene()
        pixmap = QPixmap(fileName)
        scene.addPixmap(pixmap)
        scene.dragMoveEvent = partial(self.dragMoveEvent)
        view.setScene(scene)
        view.fitInView(scene.sceneRect(), QtCore.Qt.KeepAspectRatio)
        view.show()
        if ('Payload1' in view.objectName()):
            self.txtPayloadSize.setText(str(len(value.json)))
            self.payload1 = value
            self.saveValid()
        elif ('Carrier1' in view.objectName()):
            height,width,depth = value.img.shape
            self.txtCarrierSize.setText(str(height*width))
            self.carrier1 = value
            self.chkOverride.setChecked(False)
            try:
                if (self.carrier1.payloadExists()):
                    self.lblPayloadFound.setText('>>>> Payload Found <<<<')
                    self.chkOverride.setEnabled(True)
                    self.saveValid()
                else:
                    self.lblPayloadFound.setText('')
                    self.chkOverride.setChecked(False)
                    self.chkOverride.setEnabled(False)
                    self.saveValid()
            except:
                self.lblPayloadFound.setText('')
                self.chkOverride.setChecked(False)
                self.chkOverride.setEnabled(False)
                self.saveValid()
        elif ('Carrier2' in view.objectName()):
            self.carrier2 = value
            self.carrier2path = fileName
            if (self.viewPayload2.scene()):
                scene = self.viewPayload2.scene().clear()
                self.viewPayload2.setScene(scene)
            try:
                if (self.carrier2.payloadExists()):
                    self.lblCarrierEmpty.setText('')
                    self.btnClean.setEnabled(True)
                    self.btnExtract.setEnabled(True)
                else:
                    self.lblCarrierEmpty.setText('>>>> Carrier Empty <<<<')
                    self.btnClean.setEnabled(False)
                    self.btnExtract.setEnabled(False)
            except:
                self.lblCarrierEmpty.setText('>>>> Carrier Empty <<<<')
                self.btnClean.setEnabled(False)
                self.btnExtract.setEnabled(False)

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()


if __name__ == "__main__":
    currentApp = QApplication(sys.argv)
    currentForm = Processor()

    currentForm.show()
    currentApp.exec_()