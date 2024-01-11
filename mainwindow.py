# PyQt5 modules
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import QTimer, Qt, QItemSelectionModel
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QFont, QColor, QBrush, QIcon, QPixmap

# Project modules
from py.Ui_mainwindow import Ui_MiMP3

# Utilities
import serial
from serial.tools import list_ports
import numpy as np


class MiMP3(QMainWindow, Ui_MiMP3):

    def __init__(self):
        super(MiMP3, self).__init__()
        self.setupUi(self)
        self.serial_opened = False
        self.ser = None
        self.playing = False
        self.paused = False
        self.padres = []
        self.hijos = []
        self.tree_model = QStandardItemModel()
        self.playing_index = 0

        self.font_playing = QFont()     #font para cuando esté en play
        self.font_playing.setBold(True)

        self.font_queue = QFont()   #default font
        self.Btn_buscar.clicked.connect(self.look4ports)
        self.Btn_conectar.clicked.connect(self.open_port)
        self.Btn_desconectar.clicked.connect(self.close_port)
        self.Btn_play.clicked.connect(self.play_clicked)
        self.Btn_next.clicked.connect(self.next)
        self.Btn_prev.clicked.connect(self.previous)
        self.Btn_agregar.clicked.connect(self.agregar)
        self.Btn_eliminar.clicked.connect(self.removeSel)
        self.actionClean.triggered.connect(self.listWidget.clear)
        self.actionAgregar_todos.triggered.connect(self.addAll)

        self.radioButton_normal.toggled.connect(self.normal_toggled)
        self.radioButton_urban.toggled.connect(self.urban_toggled)
        self.radioButton_clasical.toggled.connect(self.clasical_toggled)
        self.radioButton_rock.toggled.connect(self.rock_toggled)

        self.volumeSlider.sliderReleased.connect(self.volume_set)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_endofsong)
        self.look4ports()

    def look4ports(self):
        com_ports = list_ports.comports()
        self.comboBox_COMports.clear()
        if com_ports:
            for port, desc, hwid in sorted(com_ports):
                self.comboBox_COMports.addItem("{} : {}".format(port, desc))
            self.statusBar.showMessage('Puertos encontrados: {}'.format(self.comboBox_COMports.count()))
        else:
            self.statusBar.showMessage('No se encontró un puerto COM')

    def open_port(self):
        if not self.serial_opened:
            if self.comboBox_COMports.count() >= 1:
                comx = self.comboBox_COMports.currentText()
                comx = comx.split()
                try:
                    self.ser = serial.Serial(comx[0], timeout=0, baudrate=115200, parity=serial.PARITY_EVEN)
                    self.serial_opened = True
                    self.statusBar.showMessage('Puerto {} abierto'.format(comx[0]))
                except serial.SerialException:
                    self.statusBar.showMessage('No se pudo abrir el puerto')
            else:
                self.statusBar.showMessage('No hay puertos para abrir')
            if self.serial_opened:
                self.ser.write(b'C')
                self.build_tree()
        else: 
            self.statusBar.showMessage('Desconectese del puerto actual para abrir otro')

    def close_port(self):
        self.tree_model.clear()
        self.listWidget.clear()
        self.label_song_name.setText("--")
        if self.serial_opened:
            self.ser.close()
            self.statusBar.showMessage('Puerto cerrado')
            self.serial_opened = False
        else:
            self.statusBar.showMessage('No hay un puerto abierto')

    def procesar_cadena(self, cadena):
        self.padres.clear()
        self.hijos.clear()
        parent_name = []
        lineas = cadena.split('\n')
        for linea in lineas:
            elementos = linea[1:].split('/')
            padre = elementos[0]
            hijo = elementos[1][:-4]

            i=0
            father_index=-1
            if len(parent_name)>0:
                for i in range(len(parent_name)):
                    if padre == parent_name[i]:
                        father_index=i
                        break
                if(father_index!=-1):
                    self.hijos.append(QStandardItem(hijo))
                    self.padres[i].appendRow(self.hijos[-1])
                else:
                    self.padres.append(QStandardItem(padre))
                    parent_name.append(padre)
                    self.hijos.append(QStandardItem(hijo))
                    self.padres[-1].appendRow(self.hijos[-1])
            else:
                self.padres.append(QStandardItem(padre))
                parent_name.append(padre)
                self.hijos.append(QStandardItem(hijo))
                self.padres[-1].appendRow(self.hijos[-1])
            
    def build_tree(self):
        rootNode = self.tree_model.invisibleRootItem()
        
        datos_recibidos = ""
        self.ser.timeout = 5.0
        try:
            while True:
                # Lee un byte del puerto serial
                byte_recibido = self.ser.read()
                
                # Decodifica el byte a una cadena
                caracter_recibido = byte_recibido.decode('Ascii')
                
                # Agrega el caracter recibido a los datos acumulados
                datos_recibidos += caracter_recibido
                
                # Verifica si se ha alcanzado el final del archivo (EOF)
                if caracter_recibido == '\x1A':
                    break
                
            self.procesar_cadena(datos_recibidos[:-2])
            for padre in self.padres:
                rootNode.appendRow(padre)
            
            self.timer.start(500)
            self.treeView.setModel(self.tree_model)
        except serial.SerialTimeoutException:
            self.statusBar.showMessage('RX Timeout. Check connection to MP3')
        
    def removeSel(self):
        listItems=self.listWidget.selectedItems()
        if not listItems: return        
        for item in listItems:
            self.listWidget.takeItem(self.listWidget.row(item))

    def addAll(self):
        model = self.treeView.model()
        root_index = model.index(0, 0)  # Suponiendo que el índice del elemento raíz es (0, 0)

        # Iterar entre los elementos del nivel especificado
        for row in range(model.rowCount(root_index)):
            parent_index = model.index(row, 0, root_index)  # Obtener el índice del elemento padre
            self.treeView.setExpanded(parent_index, True)  # Expandir el elemento padre
            child_index = model.index(0, 0, parent_index)  # Obtener el índice del primer hijo

            # Seleccionar todos los hijos del nivel especificado
            for child_row in range(model.rowCount(child_index)):
                child_item_index = model.index(child_row, 0, child_index)
                self.treeView.selectionModel().select(child_item_index, QItemSelectionModel.Select)

    def play_clicked(self):
        if self.serial_opened:
            if self.listWidget.count() > 0:
                if self.playing and not self.paused:
                    #'\pause'
                    self.ser.write(b'A') #pause
                    self.playing = True
                    self.statusBar.showMessage('Paused')
                    self.Btn_play.setText('▶')
                    self.playing = False
                    self.paused = True
                elif not self.playing and not self.paused:
                    #'\play'
                    text = self.listWidget.item(self.playing_index).text().split('\t')
                    to_send = "L/" + text[1][1:-1] + '/' + text[0] + ".MP3" + '\x1A' #play song
                    self.ser.write(to_send.encode('utf-8'))
                    self.statusBar.showMessage('Playing')
                    self.Btn_play.setText('ll')
                    self.playing = True
                    self.paused = False
                    self.actualizarTodo()
                    self.label_song_name.setText(text[0])
                elif not self.playing and self.paused:
                    to_send = "R"   #resume
                    self.ser.write(to_send.encode('utf-8'))
                    self.statusBar.showMessage('Playing')
                    self.Btn_play.setText('ll')
                    self.playing = True
                    self.paused = False
            else:
                self.statusBar.showMessage('No hay canciones para reproducir')

    def previous(self):
        self.onRowsMoved()
        if self.playing_index > 0:
            self.playing_index -= 1
            text = self.listWidget.item(self.playing_index).text().split('\t')
            to_send = "L/" + text[1][1:-1] + '/' + text[0] + ".MP3" + '\x1A'
            self.ser.write(to_send.encode('utf-8'))
            self.actualizarTodo()
            self.label_song_name.setText(text[0])
    
    def agregar(self):
        for index in self.treeView.selectedIndexes():
            if index.parent().data() != None:
                text = index.data() + '\t[' + index.parent().data() + ']' 
                self.listWidget.addItem(text)

    def next(self):
        if self.serial_opened:
            self.onRowsMoved()
            if self.playing_index < (self.listWidget.count()-1):
                self.playing_index += 1
            else:
                self.playing_index = 0
            text = self.listWidget.item(self.playing_index).text().split('\t')
            to_send = "L/" + text[1][1:-1] + '/' + text[0] + ".MP3" + '\x1A'
            self.ser.write(to_send.encode('utf-8'))
            self.actualizarTodo()
            self.label_song_name.setText(text[0])

    def actualizarTodo(self):
        for item in range(self.listWidget.count()):
            if item == self.playing_index and self.listWidget.item(item).text()[0] != "\u2192":
                self.listWidget.item(item).setText("\u2192" + self.listWidget.item(item).text())
                self.listWidget.item(item).setFont(self.font_playing)
                self.listWidget.item(item).setBackground(QColor("lightblue"))
            else:
                if self.listWidget.item(item).text()[0] == "\u2192":
                    self.listWidget.item(item).setText(self.listWidget.item(item).text()[1:])
                self.listWidget.item(item).setFont(self.font_queue)
                self.listWidget.item(item).setBackground(QBrush())

    def onRowsMoved(self):
        for item in range(self.listWidget.count()):
            if self.listWidget.item(item).text()[0] == "\u2192":
                self.playing_index = item

    def normal_toggled(self, selected):
        if selected and self.serial_opened:
            self.ser.write(b'N')
             
    def urban_toggled(self, selected):
        if selected and self.serial_opened:
            self.ser.write(b'U')
    
    def clasical_toggled(self, selected):
        if selected and self.serial_opened:
            self.ser.write(b'O')
    
    def rock_toggled(self, selected):
        if selected and self.serial_opened:
            self.ser.write(b'K')

    def volume_set(self):
        if self.serial_opened:
            val = self.volumeSlider.value()
            if val<10:
                to_send = "V0" + str(val)
            else:
                to_send = "V" + str(val)
            self.ser.write(to_send.encode('utf-8'))

    def check_endofsong(self):
        if self.serial_opened:
            self.ser.timeout = 0.05
            a = self.ser.read(1)
            if a == b'E':
                self.next()
            self.ser.timeout = 0

    def closeEvent(self, event):
        if self.serial_opened:
            self.ser.write(b'X')
            self.close_port()