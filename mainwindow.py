# PyQt5 modules
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import QTimer, Qt, QItemSelectionModel
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QFont, QColor, QBrush

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
        # self.list_model = QStandardItemModel()
        # self.listView.setModel(self.list_model)

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
        # self.build_tree()
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
                    self.ser = serial.Serial(comx[0], timeout=0, baudrate=115200)
                    self.serial_opened = True
                    self.statusBar.showMessage('Puerto {} abierto'.format(comx[0]))
                except serial.SerialException:
                    self.statusBar.showMessage('No se pudo abrir el puerto')
            else:
                self.statusBar.showMessage('No hay puertos para abrir')
            if self.serial_opened:
                self.ser.write(b'\connect')
                self.build_tree()
        else: 
            self.statusBar.showMessage('Desconectese del puerto actual para abrir otro')

    def close_port(self):
        if self.serial_opened:
            self.ser.close()
            self.statusBar.showMessage('Puerto cerrado')
            self.serial_opened = False
        else:
            self.statusBar.showMessage('No hay un puerto abierto')

    def procesar_cadena(self, cadena):
        self.padres.clear()
        self.hijos.clear()
        lineas = cadena.split('\n')
        
        for linea in lineas:
            elementos = linea.split('.')
            padre = elementos[0]
            hijos = elementos[1:]
            
            self.padres.append(QStandardItem(padre))

            for hijo in hijos:
                self.hijos.append(QStandardItem(hijo))
                self.padres[-1].appendRow(self.hijos[-1])

    def build_tree(self):
        rootNode = self.tree_model.invisibleRootItem()
        
        datos_recibidos = ""
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
            
        self.procesar_cadena(datos_recibidos)
        for padre in self.padres:
            rootNode.appendRow(padre)

        # padre = QStandardItem("papa")
        # hijo =QStandardItem("Dimas")
        # hijo1 =QStandardItem("Dimas1")
        # hijo2 =QStandardItem("Dimas2")
        # hijo3 =QStandardItem("Dimas3")
        # padre.appendRows([hijo, hijo1, hijo2])
        # madre = QStandardItem("mama")
        # madre.appendRow(hijo3)

        # rootNode.appendRow(padre)
        # rootNode.appendRow(madre)

        self.treeView.setModel(self.tree_model)

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
        if self.playing and not self.paused:
            #'\pause'
            self.ser.write(b'\pause')
            self.playing = True
            self.statusBar.showMessage('Paused')
            self.Btn_play.setText('PLAY')
            self.playing = False
            self.paused = True
        elif not self.playing and not self.paused:
            #'\play'
            text = self.listWidget.item(self.playing_index).text().split('\t')
            to_send = "\play\\" + text[1][1:-1] + '\\' + text[0]
            self.ser.write(to_send.encode('utf-8'))
            self.statusBar.showMessage('Playing')
            self.Btn_play.setText('PAUSE')
            self.playing = True
            self.paused = False
            self.actualizarTodo()
            self.label_song_name.setText(text[0])
        elif not self.playing and self.paused:
            to_send = "\\resume"
            self.ser.write(to_send.encode('utf-8'))
            self.statusBar.showMessage('Playing')
            self.Btn_play.setText('PAUSE')
            self.playing = True
            self.paused = False
            
        # for i in range(self.listWidget.count()):
        #     print(self.listWidget.item(i).text())

    def previous(self):
        self.onRowsMoved()
        if self.playing_index > 0:
            self.playing_index -= 1
            text = self.listWidget.item(self.playing_index).text().split('\t')
            to_send = "\play\\" + text[1][1:-1] + '\\' + text[0]
            self.ser.write(to_send.encode('utf-8'))
            self.actualizarTodo()
        #anterior
        pass
    
    def agregar(self):
        for index in self.treeView.selectedIndexes():
            if index.parent().data() != None:
                text = index.data() + '\t[' + index.parent().data() + ']' 
                self.listWidget.addItem(text)

    def next(self):
        self.onRowsMoved()
        if self.playing_index < (self.listWidget.count()-1):
            self.playing_index += 1
        else:
            self.playing_index = 0
            # print(self.playing_index)
        text = self.listWidget.item(self.playing_index).text().split('\t')
        to_send = "\play\\" + text[1][1:-1] + '\\' + text[0]
        self.ser.write(to_send.encode('utf-8'))
        self.actualizarTodo()
        #siguiente
        pass

    def actualizarTodo(self):
        for item in range(self.listWidget.count()):
            if item == self.playing_index and self.listWidget.item(item).text()[0] != "\u2192":
                # print(item)
                # print(">" + self.listWidget.item(item).text())
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

