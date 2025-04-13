# -*- coding: utf-8 -*-


from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QListWidgetItem, QLabel
from PyQt5.QtWidgets import QMessageBox
import minecraft_launcher_lib as mll
from random_username.generate import generate_username
from uuid import uuid1
from portablemc.standard import Version
from portablemc.forge import ForgeVersion
import requests
import modrinth
import os
import ctypes
from skinpy import Skin, Perspective

minecraft_directory = mll.utils.get_minecraft_directory()
Form = None


class LaunchThread(QThread):
    launch_setup_signal = pyqtSignal(
        str,
        str,
        int,
        str,
        str,
        QtWidgets.QWidget,
        bool,
        tuple
    )
    progress_update_signal = pyqtSignal(str)

    version_id = ''
    username = ''
    progress_label = ''

    forge_install = False

    def __init__(self):
        super().__init__()
        self.launch_setup_signal.connect(self.launch_setup)
        self.minecraft_directory = minecraft_directory

    def launch_setup(self, version_id, username, RAM, jvm, lang, Form, hide, res):
        self.version_id = version_id
        self.username = username
        self.RAM = RAM
        self.jvm = jvm.split(';') if jvm else []
        self.jvm.append(f'-Xmx{RAM}M')
        self.jvm.append(f'-Xmx{RAM}M')
        self.lang = lang
        self.Form = Form
        self.hide = hide
        self.res = res


    def update_progress_label(self, value):
        self.progress_label = value
        self.progress_update_signal.emit(self.progress_label)

    def run(self):
        self.update_progress_label("Checking Minecraft version...")

        self.update_progress_label(f"Installing Minecraft version {self.version_id}...")
        self.update_progress_label(f"Set language {self.lang}...")
        if os.path.exists(os.path.join(minecraft_directory, "mods")):
            print(os.listdir(os.path.join(minecraft_directory, "mods")))

            try:
                if self.hide:
                    Form.hide()
                version = ForgeVersion(self.version_id + '-recommended')
                version.resolution = self.res
                version.fixes[Version.FIX_LWJGL] = '3.3.2'
                env = version.install()
                env.args_replacements['auth_player_name'] = self.username
                env.args_replacements['auth_uuid'] = str(uuid1())
                print(env.args_replacements)
                jv = env.jvm_args
                for i in self.jvm:
                    jv.append(i)
                env.jvm_args = jv
                print(env.jvm_args)
                print(os.listdir(f'{minecraft_directory}\\versions'))
                env.run()
                if self.hide:
                    Form.show()
            except Exception as e:
                print(f"Ошибка при запуске Minecraft: {e}")
        else:
            if self.hide:
                Form.hide()
            version = Version(self.version_id)
            version.resolution = self.res
            version.fixes[Version.FIX_LWJGL] = '3.3.2'
            env = version.install()
            env.args_replacements['auth_player_name'] = self.username
            env.args_replacements['auth_uuid'] = str(uuid1())
            print(env.args_replacements)
            jv = env.jvm_args
            for i in self.jvm:
                jv.append(i)
            env.jvm_args = jv
            print(env.jvm_args)
            env.run()
            if self.hide:
                Form.show()
class AddThread(QThread):
    mod_thread = pyqtSignal(modrinth.Projects.ModrinthProject, QtWidgets.QListWidget)

    project = None
    listwidget = None

    def __init__(self):
        super().__init__()
        self.mod_thread.connect(self.add_setup)
    def add_setup(self, project, listwidget):
        self.project = project
        self.listwidget = listwidget
    def run(self):
        """
                Добавляет мод в listWidget_2 с постером и названием.
                """

        # Загружаем постер мода
        if self.project.iconURL:
            response = requests.get(self.project.iconURL)
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            global icon
            icon = QtGui.QIcon(pixmap)
        item = QListWidgetItem(parent=self.listwidget)
        item.setText(self.project.name)
        item.setIcon(icon)

        # Устанавливаем виджет в QListWidgetItem
        self.listwidget.addItem(item)

        item.setData(Qt.UserRole, self.project.id)
class ModSearch(QThread):
    search_thread = pyqtSignal(str, QtWidgets.QListWidget)
    add_thread = AddThread()


    query = ''
    listwidget = None

    def __init__(self):
        super().__init__()
        self.search_thread.connect(self.search_setup)
    def search_setup(self, query, listwidget):
        self.query = query
        self.listwidget = listwidget
    def run(self):
        """
                Поиск модов по запросу из lineEdit_3 и отображение их в listWidget_2.
                """
        # Получаем текст из поля поиска
        if not self.query:
            return

        # Очищаем listWidget_2 перед новым поиском
        self.listwidget.clear()

        # Ищем моды через Modrinth API
        search_results = modrinth.Projects.Search(self.query, filters='categories="forge"')

        for project in search_results.hits:
            self.add_thread.add_setup(project, self.listwidget)
            self.add_thread.run()


class ModInstall(QThread):
    search_thread = pyqtSignal(QtWidgets.QListWidget, QtWidgets.QListWidget, QtWidgets.QComboBox)

    listwidget = None
    listwidget2 = None
    combobox = None

    def __init__(self):
        super().__init__()
        self.search_thread.connect(self.install_setup)

    def install_setup(self, listwidget, listwidget2, combobox):
        self.listwidget = listwidget
        self.listwidget2 = listwidget2
        self.combobox = combobox

    def run(self):
        """
        Скачивает и устанавливает выбранный мод.
                                             """
        selected_item = self.listwidget.currentItem()
        if not selected_item:
            return

        mod_id = selected_item.data(Qt.UserRole)  # Получаем ID мода
        if not mod_id:
            return

        # Получаем информацию о моде
        project = modrinth.Projects.ModrinthProject(mod_id)

        versions = project.getAllVersions()
        for i in versions:
            if (self.combobox.currentText() in i.gameVersions) and ('forge' in i.loaders):
                self.latest_version = i
                break
        # Скачиваем файл мода
        download_url = self.latest_version.getDownload(self.latest_version.getFiles())
        mod_filename = os.path.basename(download_url)
        mod_path = os.path.join(minecraft_directory, "mods", mod_filename)

        # Создаем папку mods, если её нет
        os.makedirs(os.path.join(minecraft_directory, "mods"), exist_ok=True)

        # Скачиваем файл
        response = requests.get(download_url)
        with open(mod_path, "wb") as f:
            f.write(response.content)
        print(f"Мод {project.name} успешно установлен в {mod_path}")
        if project.iconURL:
            response = requests.get(project.iconURL)
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            global icon
            icon = QtGui.QIcon(pixmap)
        item = QListWidgetItem(parent=self.listwidget2)
        item.setText(project.name)
        item.setIcon(icon)
        # Устанавливаем виджет в QListWidgetItem
        self.listwidget2.addItem(item)



class Ui_Form(object):
    def __init__(self):
        super().__init__()
        self.user32 = ctypes.windll.user32
        self.user32.SetProcessDPIAware()
        self.skin_ = ''
        self.dir_left_right = 0
        self.dir_front_back = 0
        self.dir_up_down = 0
    def setupUi(self, Form):
        self.lang = 'en'
        self.hide = False
        self.currentIndex = 999

        Form.setObjectName("Form")
        Form.resize(390, 467)
        Form.setFixedSize(390, 467)
        Form.setStyleSheet("background-color: rgb(48, 48, 48);")
        Form.setWindowIcon(QtGui.QIcon('icon.png'))
        self.label = QtWidgets.QLabel(Form)
        self.label.setGeometry(QtCore.QRect(10, 0, 371, 121))
        self.label.setText("")
        self.label.setPixmap(QtGui.QPixmap("ico.png"))
        self.label.setObjectName("label")
        self.tabWidget = QtWidgets.QTabWidget(Form)
        self.tabWidget.setGeometry(QtCore.QRect(0, 100, 391, 371))
        self.tabWidget.setObjectName("tabWidget")
        self.game = QtWidgets.QWidget()
        self.game.setObjectName("game")
        self.label_2 = QtWidgets.QLabel(self.game)
        self.label_2.setGeometry(QtCore.QRect(10, 10, 371, 41))
        self.label_2.setStyleSheet("font: 10pt \"MS Shell Dlg 2\";\n"
                                   "color: rgb(255, 255, 255);")
        self.label_2.setObjectName("label_2")
        self.textEdit = QtWidgets.QTextEdit(self.game)
        self.textEdit.setGeometry(QtCore.QRect(10, 40, 371, 261))
        self.textEdit.setObjectName("textEdit")
        self.lineEdit = QtWidgets.QLineEdit(self.game)
        self.lineEdit.setGeometry(QtCore.QRect(10, 310, 151, 20))
        self.lineEdit.setStyleSheet("color: rgb(255, 255, 255);")
        self.lineEdit.setObjectName("lineEdit")
        self.pushButton = QtWidgets.QPushButton(self.game)
        self.pushButton.setGeometry(QtCore.QRect(260, 310, 121, 23))
        self.pushButton.setStyleSheet("background-color: rgb(255, 255, 255);")
        self.pushButton.setObjectName("pushButton")
        self.pushButton.clicked.connect(self.launch_game)
        self.comboBox = QtWidgets.QComboBox(self.game)
        self.comboBox.setGeometry(QtCore.QRect(170, 310, 81, 22))
        self.comboBox.setStyleSheet("color: rgb(255, 255, 255);")
        self.comboBox.setObjectName("comboBox")

        self.minecraft_directory = mll.utils.get_minecraft_directory()

        self.tabWidget.addTab(self.game, "")
        self.settings = QtWidgets.QWidget()
        self.settings.setObjectName("settings")
        self.label_3 = QtWidgets.QLabel(self.settings)
        self.label_3.setGeometry(QtCore.QRect(10, 10, 61, 31))
        self.label_3.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_3.setObjectName("label_3")
        self.comboBox_2 = QtWidgets.QComboBox(self.settings)
        self.comboBox_2.setGeometry(QtCore.QRect(80, 10, 101, 31))
        self.comboBox_2.setStyleSheet("color: rgb(255, 255, 255);")
        self.comboBox_2.setObjectName("comboBox_2")
        self.comboBox_2.addItem("")
        self.comboBox_2.addItem("")
        self.comboBox_2.currentIndexChanged.connect(self.text_transl)

        self.label_4 = QtWidgets.QLabel(self.settings)
        self.label_4.setGeometry(QtCore.QRect(10, 60, 47, 21))
        self.label_4.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_4.setObjectName("label_4")
        self.horizontalSlider = QtWidgets.QSlider(self.settings)
        self.horizontalSlider.setGeometry(QtCore.QRect(70, 60, 131, 22))
        self.horizontalSlider.setMaximum(9256)
        self.horizontalSlider.setValue(2020)
        self.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider.setObjectName("horizontalSlider")
        self.horizontalSlider.valueChanged.connect(self.text_change)
        self.label_5 = QtWidgets.QLabel(self.settings)
        self.label_5.setGeometry(QtCore.QRect(10, 100, 81, 31))
        self.label_5.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_5.setObjectName("label_5")
        self.comboBox_3 = QtWidgets.QComboBox(self.settings)
        self.comboBox_3.setGeometry(QtCore.QRect(100, 101, 81, 31))
        self.comboBox_3.setStyleSheet("color: rgb(255, 255, 255);")
        self.comboBox_3.setObjectName("comboBox_3")
        self.comboBox_3.addItem("")
        self.comboBox_3.addItem("")
        self.comboBox_3.currentIndexChanged.connect(self.act)
        self.label_6 = QtWidgets.QLabel(self.settings)
        self.label_6.setGeometry(QtCore.QRect(10, 140, 81, 31))
        self.label_6.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_6.setObjectName("label_6")
        self.lineEdit_2 = QtWidgets.QLineEdit(self.settings)
        self.lineEdit_2.setGeometry(QtCore.QRect(90, 139, 211, 31))
        self.lineEdit_2.setStyleSheet("color: rgb(255, 255, 255);")
        self.lineEdit_2.setObjectName("lineEdit_2")
        self.label_9 = QtWidgets.QLabel(self.settings)
        self.label_9.setGeometry(QtCore.QRect(210, 60, 71, 21))
        self.label_9.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_9.setObjectName("label_9")
        self.tabWidget.addTab(self.settings, "")
        self.mods = QtWidgets.QWidget()
        self.mods.setObjectName("mods")
        self.tabWidget_2 = QtWidgets.QTabWidget(self.mods)
        self.tabWidget_2.setGeometry(QtCore.QRect(0, 0, 391, 351))
        self.tabWidget_2.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.tabWidget_2.setTabPosition(QtWidgets.QTabWidget.West)
        self.tabWidget_2.setObjectName("tabWidget_2")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.label_7 = QtWidgets.QLabel(self.tab)
        self.label_7.setGeometry(QtCore.QRect(10, 10, 351, 21))
        self.label_7.setStyleSheet("color: rgb(255, 255, 255);\n"
                                   "font: 10pt \"MS Shell Dlg 2\";")
        self.label_7.setObjectName("label_7")
        self.listWidget = QtWidgets.QListWidget(self.tab)
        self.listWidget.setGeometry(QtCore.QRect(10, 40, 351, 291))
        self.listWidget.setStyleSheet("color: rgb(255, 255, 255);")
        self.listWidget.setObjectName("listWidget")
        self.tabWidget_2.addTab(self.tab, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.label_8 = QtWidgets.QLabel(self.tab_2)
        self.label_8.setGeometry(QtCore.QRect(10, 10, 51, 21))
        self.label_8.setStyleSheet("color: rgb(255, 255, 255);\n"
                                   "font: 12pt \"MS Shell Dlg 2\";")
        self.label_8.setObjectName("label_8")
        self.listWidget_2 = QtWidgets.QListWidget(self.tab_2)
        self.listWidget_2.setGeometry(QtCore.QRect(10, 40, 341, 261))
        self.listWidget_2.setStyleSheet("color: rgb(255, 255, 255);")
        self.listWidget_2.setObjectName("listWidget_2")
        self.listWidget_2.setIconSize(QtCore.QSize(64, 64))
        self.lineEdit_3 = QtWidgets.QLineEdit(self.tab_2)
        self.lineEdit_3.setGeometry(QtCore.QRect(70, 10, 201, 20))
        self.lineEdit_3.setStyleSheet("color: rgb(255, 255, 255);")
        self.lineEdit_3.setObjectName("lineEdit_3")
        self.pushButton_2 = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_2.setGeometry(QtCore.QRect(280, 10, 75, 23))
        self.pushButton_2.setStyleSheet("background-color: rgb(255, 255, 255);")
        self.pushButton_2.setObjectName("pushButton_2")
        self.pushButton_3 = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_3.setGeometry(QtCore.QRect(280, 310, 75, 23))
        self.pushButton_3.setStyleSheet("background-color: rgb(255, 255, 255);")
        self.pushButton_3.setObjectName("pushButton_3")
        self.tabWidget_2.addTab(self.tab_2, "")
        self.tabWidget.addTab(self.mods, "")

        for i in mll.utils.get_available_versions(self.minecraft_directory):
            if i["type"] == "release":
                self.comboBox.addItem(i["id"])

        self.pushButton_5 = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_5.setGeometry(QtCore.QRect(10, 310, 21, 21))
        self.pushButton_5.setStyleSheet("background-color: rgb(255, 255, 255);")
        self.pushButton_5.setObjectName("pushButton_5")
        self.pushButton_5.clicked.connect(self.upper_index)
        self.pushButton_5.setText('')

        self.pushButton_6 = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_6.setGeometry(QtCore.QRect(40, 310, 21, 21))
        self.pushButton_6.setStyleSheet("background-color: rgb(255, 255, 255);")
        self.pushButton_6.setObjectName("pushButton_6")
        self.pushButton_6.clicked.connect(self.lower_index)
        self.pushButton_6.setText('')

        self.label_10 = QtWidgets.QLabel(self.settings)
        self.label_10.setGeometry(QtCore.QRect(10, 180, 81, 51))
        self.label_10.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_10.setText("")
        self.label_10.setObjectName("label_10")

        self.label_11 = QtWidgets.QLabel(self.settings)
        self.label_11.setGeometry(QtCore.QRect(280, 180, 61, 21))
        self.label_11.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_11.setText("")
        self.label_11.setObjectName("label_10")

        self.label_12 = QtWidgets.QLabel(self.settings)
        self.label_12.setGeometry(QtCore.QRect(280, 210, 61, 21))
        self.label_12.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_12.setText("")
        self.label_12.setObjectName("label_10")

        self.horizontalSlider_2 = QtWidgets.QSlider(self.settings)
        self.horizontalSlider_2.setGeometry(QtCore.QRect(100, 180, 102, 22))
        self.horizontalSlider_2.setMaximum(self.user32.GetSystemMetrics(0))
        self.horizontalSlider_2.setValue(940)
        self.horizontalSlider_2.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_2.setObjectName("horizontalSlider_2")
        self.horizontalSlider_2.valueChanged.connect(self.res_x_sl_update)

        self.horizontalSlider_3 = QtWidgets.QSlider(self.settings)
        self.horizontalSlider_3.setGeometry(QtCore.QRect(100, 210, 102, 22))
        self.horizontalSlider_3.setMaximum(self.user32.GetSystemMetrics(1))
        self.horizontalSlider_3.setValue(350)
        self.horizontalSlider_3.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_3.setObjectName("horizontalSlider_3")
        self.horizontalSlider_3.valueChanged.connect(self.res_y_sl_update)

        self.lineEdit_4 = QtWidgets.QLineEdit(self.settings)
        self.lineEdit_4.setGeometry(QtCore.QRect(210, 180, 61, 20))
        self.lineEdit_4.setStyleSheet("color: rgb(255, 255, 255);")
        self.lineEdit_4.setObjectName("lineEdit_4")
        self.lineEdit_4.setText(str(self.horizontalSlider_2.value()))
        self.lineEdit_4.textEdited.connect(self.res_x_te_update)

        self.lineEdit_5 = QtWidgets.QLineEdit(self.settings)
        self.lineEdit_5.setGeometry(QtCore.QRect(210, 210, 61, 20))
        self.lineEdit_5.setStyleSheet("color: rgb(255, 255, 255);")
        self.lineEdit_5.setObjectName("lineEdit_5")
        self.lineEdit_5.setText(str(self.horizontalSlider_3.value()))
        self.lineEdit_5.textEdited.connect(self.res_y_te_update)

        self.skin = QtWidgets.QWidget()
        self.skin.setObjectName("skin")

        self.label_13 = QtWidgets.QLabel(self.skin)
        self.label_13.setGeometry(QtCore.QRect(20, 20, 111, 21))
        self.label_13.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_13.setText("")
        self.label_13.setObjectName("label_13")

        self.label_14 = QtWidgets.QLabel(self.skin)
        self.label_14.setGeometry(QtCore.QRect(20, 60, 171, 221))
        self.label_14.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_14.setText("")
        self.label_14.setObjectName("label_14")

        self.label_15 = QtWidgets.QLabel(self.skin)
        self.label_15.setGeometry(QtCore.QRect(300, 60, 71, 16))
        self.label_15.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_15.setText("")
        self.label_15.setObjectName("label_15")

        self.label_16 = QtWidgets.QLabel(self.skin)
        self.label_16.setGeometry(QtCore.QRect(300, 90, 71, 16))
        self.label_16.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_16.setText("")
        self.label_16.setObjectName("label_16")

        self.label_17 = QtWidgets.QLabel(self.skin)
        self.label_17.setGeometry(QtCore.QRect(300, 120, 71, 16))
        self.label_17.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_17.setText("")
        self.label_17.setObjectName("label_17")

        self.horizontalScrollBar = QtWidgets.QScrollBar(self.skin)
        self.horizontalScrollBar.setGeometry(QtCore.QRect(210, 60, 81, 16))
        self.horizontalScrollBar.setOrientation(Qt.Horizontal)
        self.horizontalScrollBar.setPageStep(1)
        self.horizontalScrollBar.setMaximum(1)
        self.horizontalScrollBar.setValue(0)
        self.horizontalScrollBar.setObjectName('horizontalScrollBar')
        self.horizontalScrollBar.valueChanged.connect(self.left_right)

        self.horizontalScrollBar_2 = QtWidgets.QScrollBar(self.skin)
        self.horizontalScrollBar_2.setGeometry(QtCore.QRect(210, 90, 81, 16))
        self.horizontalScrollBar_2.setOrientation(Qt.Horizontal)
        self.horizontalScrollBar_2.setPageStep(1)
        self.horizontalScrollBar_2.setMaximum(1)
        self.horizontalScrollBar_2.setValue(0)
        self.horizontalScrollBar_2.setObjectName('horizontalScrollBar_2')
        self.horizontalScrollBar_2.valueChanged.connect(self.front_back)

        self.horizontalScrollBar_3 = QtWidgets.QScrollBar(self.skin)
        self.horizontalScrollBar_3.setGeometry(QtCore.QRect(210, 120, 81, 16))
        self.horizontalScrollBar_3.setOrientation(Qt.Horizontal)
        self.horizontalScrollBar_3.setPageStep(1)
        self.horizontalScrollBar_3.setMaximum(1)
        self.horizontalScrollBar_3.setValue(0)
        self.horizontalScrollBar_3.setObjectName('horizontalScrollBar_3')
        self.horizontalScrollBar_3.valueChanged.connect(self.up_down)

        self.pushButton_7 = QtWidgets.QPushButton(self.skin)
        self.pushButton_7.setGeometry(QtCore.QRect(140, 20, 101, 23))
        self.pushButton_7.setStyleSheet("color: rgb(255, 255, 255);")
        self.pushButton_7.setObjectName("pushButton_7")
        self.pushButton_7.setText('')
        self.pushButton_7.clicked.connect(self.skin_select)

        self.pushButton_8 = QtWidgets.QPushButton(self.skin)
        self.pushButton_8.setGeometry(QtCore.QRect(300, 270, 75, 23))
        self.pushButton_8.setStyleSheet("color: rgb(255, 255, 255);")
        self.pushButton_8.setObjectName("pushButton_8")
        self.pushButton_8.setText('')

        self.tabWidget.addTab(self.skin, "")

        self.launch_thread = LaunchThread()
        self.launch_thread.progress_update_signal.connect(self.update_progress)

        self.search_thread = ModSearch()

        self.mod_install_thread = ModInstall()


        self.retranslateUi(Form)
        self.tabWidget.setCurrentIndex(0)
        self.tabWidget_2.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(Form)

        # Подключаем кнопки поиска и установки модов
        self.pushButton_2.clicked.connect(self.search_mods)
        self.pushButton_3.clicked.connect(self.install_selected_mod)

    def search_mods(self):
        """
        Поиск модов по запросу из lineEdit_3 и отображение их в listWidget_2.
        """
        self.search_thread.search_thread.emit(self.lineEdit_3.text(), self.listWidget_2)
        self.search_thread.start()

    def install_selected_mod(self):
        """
        Скачивает и устанавливает выбранный мод.
        """
        self.mod_install_thread.search_thread.emit(self.listWidget_2, self.listWidget, self.comboBox)
        self.mod_install_thread.start()

    def upper_index(self):
        if self.currentIndex == 999:
            self.currentIndex = 0

        self.currentIndex -= 1
        if self.currentIndex < 0:
            self.currentIndex = 0

        self.listWidget_2.setCurrentRow(self.currentIndex)

    def lower_index(self):
        if self.currentIndex == 999:
            self.currentIndex = 0
        try:
            self.currentIndex += 1
            if self.currentIndex >= self.listWidget_2.count():
                self.currentIndex = self.listWidget_2.count() - 1
            self.listWidget_2.setCurrentRow(self.currentIndex)
        except Exception as E:
            print(E)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "P:Launcher Remake"))
        self.label_2.setText(_translate("Form", "Processes"))
        self.lineEdit.setPlaceholderText(_translate("Form", "Nickname"))
        self.pushButton.setText(_translate("Form", "Launch"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.game), _translate("Form", "Game"))
        self.label_3.setText(_translate("Form", "Language"))
        self.comboBox_2.setItemText(0, _translate("Form", "EN (English)"))
        self.comboBox_2.setItemText(1, _translate("Form", "Ru (Russian)"))
        self.label_4.setText(_translate("Form", "RAM"))
        self.label_5.setText(_translate("Form", "Action on launch"))
        self.comboBox_3.setItemText(0, _translate("Form", "None"))
        self.comboBox_3.setItemText(1, _translate("Form", "Hide"))
        self.label_6.setText(_translate("Form", "Arguments"))
        self.lineEdit_2.setPlaceholderText(_translate("Form", "JVM Arguments"))
        self.label_9.setText(_translate("Form", "2020/9256 M"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.settings), _translate("Form", "Settings"))
        self.label_7.setText(_translate("Form", "Installed"))
        self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.tab), _translate("Form", "Installed"))
        self.label_8.setText(_translate("Form", "Install"))
        self.lineEdit_3.setPlaceholderText(_translate("Form", "Search..."))
        self.pushButton_2.setText(_translate("Form", "Search"))
        self.pushButton_3.setText(_translate("Form", "Install"))
        self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.tab_2), _translate("Form", "Install"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.mods), _translate("Form", "Mods"))
        self.pushButton_5.setText(_translate('Form', '↑'))
        self.pushButton_6.setText(_translate('Form', '↓'))

        self.label_10.setText(_translate("Form", "Resolution"))
        self.label_11.setText(_translate("Form", f"/ {self.user32.GetSystemMetrics(0)}"))
        self.label_12.setText(_translate("Form", f"/ {self.user32.GetSystemMetrics(1)}"))

        self.label_13.setText(_translate("Form", "Skin Select"))
        self.label_14.setText(_translate("Form", ""))
        self.label_15.setText(_translate("Form", "Left"))
        self.label_16.setText(_translate("Form", "Back"))
        self.label_17.setText(_translate("Form", "Up"))

        self.tabWidget.setTabText(self.tabWidget.indexOf(self.skin), _translate("Form", "Skin"))

        self.pushButton_7.setText(_translate("Form", "Select"))
        self.pushButton_8.setText(_translate("Form", "Save"))




    def text_change(self):
        self.label_9.setText(f"{self.horizontalSlider.value()}/9256 M")

    def text_transl(self, index):
        if index == 0:
            self.lang = 'en'
            _translate = QtCore.QCoreApplication.translate
            Form.setWindowTitle(_translate("Form", "P:Launcher Remake"))
            self.label_2.setText(_translate("Form", "Processes"))
            self.lineEdit.setPlaceholderText(_translate("Form", "Nickname"))
            self.pushButton.setText(_translate("Form", "Launch"))
            self.tabWidget.setTabText(self.tabWidget.indexOf(self.game), _translate("Form", "Game"))
            self.label_3.setText(_translate("Form", "Language"))
            self.comboBox_2.setItemText(0, _translate("Form", "EN (English)"))
            self.comboBox_2.setItemText(1, _translate("Form", "Ru (Russian)"))
            self.label_4.setText(_translate("Form", "RAM"))
            self.label_5.setText(_translate("Form", "Action on launch"))
            self.comboBox_3.setItemText(0, _translate("Form", "None"))
            self.comboBox_3.setItemText(1, _translate("Form", "Hide"))
            self.label_6.setText(_translate("Form", "Arguments"))
            self.lineEdit_2.setPlaceholderText(_translate("Form", "JVM Arguments"))
            self.label_9.setText(_translate("Form", "2020/9256 M"))
            self.tabWidget.setTabText(self.tabWidget.indexOf(self.settings), _translate("Form", "Settings"))
            self.label_7.setText(_translate("Form", "Installed"))
            self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.tab), _translate("Form", "Installed"))
            self.label_8.setText(_translate("Form", "Install"))
            self.lineEdit_3.setPlaceholderText(_translate("Form", "Search..."))
            self.pushButton_2.setText(_translate("Form", "Search"))
            self.pushButton_3.setText(_translate("Form", "Install"))
            self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.tab_2), _translate("Form", "Install"))
            self.tabWidget.setTabText(self.tabWidget.indexOf(self.mods), _translate("Form", "Mods"))
            self.tabWidget.setTabText(self.tabWidget.indexOf(self.skin), _translate("Form", "Skin"))
            self.label_10.setText(_translate("Form", "Resolution"))
            self.label_13.setText(_translate("Form", "Skin Select"))
            self.pushButton_7.setText(_translate("Form", "Select"))
            self.pushButton_8.setText(_translate("Form", "Save"))
            self.label_15.setText(_translate("Form", "Left"))
            self.label_16.setText(_translate("Form", "Back"))
            self.label_17.setText(_translate("Form", "Up"))
        if index == 1:
            self.lang = 'ru'
            _translate = QtCore.QCoreApplication.translate
            Form.setWindowTitle(_translate("Form", "P:Launcher Remake"))
            self.label_2.setText(_translate("Form", "Процессы"))
            self.lineEdit.setPlaceholderText(_translate("Form", "Ник"))
            self.pushButton.setText(_translate("Form", "Запуск"))
            self.tabWidget.setTabText(self.tabWidget.indexOf(self.game), _translate("Form", "Игра"))
            self.label_3.setText(_translate("Form", "Язык"))
            self.comboBox_2.setItemText(0, _translate("Form", "EN (Русский)"))
            self.comboBox_2.setItemText(1, _translate("Form", "Ru (Русский)"))
            self.label_4.setText(_translate("Form", "Оп-ра"))
            self.label_5.setText(_translate("Form", "Действия"))
            self.comboBox_3.setItemText(0, _translate("Form", "Ничего"))
            self.comboBox_3.setItemText(1, _translate("Form", "Спрятать"))
            self.label_6.setText(_translate("Form", "Аргументы"))
            self.lineEdit_2.setPlaceholderText(_translate("Form", "JVM Аргументы"))
            self.label_9.setText(_translate("Form", "2020/9256 M"))
            self.tabWidget.setTabText(self.tabWidget.indexOf(self.settings), _translate("Form", "Настройки"))
            self.label_7.setText(_translate("Form", "Установленные"))
            self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.tab), _translate("Form", "Установленные"))
            self.label_8.setText(_translate("Form", "Установить"))
            self.lineEdit_3.setPlaceholderText(_translate("Form", "Поиск..."))
            self.pushButton_2.setText(_translate("Form", "Поиск"))
            self.pushButton_3.setText(_translate("Form", "Установить"))
            self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.tab_2), _translate("Form", "Установить"))
            self.tabWidget.setTabText(self.tabWidget.indexOf(self.mods), _translate("Form", "Моды"))
            self.tabWidget.setTabText(self.tabWidget.indexOf(self.skin), _translate("Form", "Скин"))
            self.label_10.setText(_translate("Form", "Размер \nэкрана"))
            self.label_13.setText(_translate("Form", "Выбор скина"))
            self.pushButton_7.setText(_translate("Form", "Выбрать"))
            self.pushButton_8.setText(_translate("Form", "Сохранить"))
            self.label_15.setText(_translate("Form", "Лево"))
            self.label_16.setText(_translate("Form", "Зад"))
            self.label_17.setText(_translate("Form", "Верх"))

    def act(self, index):
        if index == 0:
            self.hide = False
        elif index == 1:
            self.hide = True

    def update_progress(self, label):
        self.textEdit.setText(self.textEdit.toPlainText() + f'\n{label}')
        print(label)

    def launch_game(self):
        self.textEdit.clear()  # Очищаем текстовое поле перед запуском

        if self.lineEdit.text() == '':
            self.lineEdit.setText(generate_username()[0])
        self.launch_thread.launch_setup_signal.emit(
            self.comboBox.currentText(), #Установка версии
            self.lineEdit.text(), #Ник
            self.horizontalSlider.value(), #Опра
            self.lineEdit_2.text(), #JVM аргументы
            self.lang, #Язык
            Form, #окно
            self.hide, #Условия скрывания окна
            (                                       #Размер экрана
                self.horizontalSlider_2.value(),    #X
                self.horizontalSlider_3.value()     #Y
            )
        )
        self.launch_thread.start()
    def res_x_sl_update(self, value):
        self.lineEdit_4.setText(str(value))
    def res_y_sl_update(self, value):
        self.lineEdit_5.setText(str(value))
    def res_x_te_update(self):
        if self.lineEdit_4.text() != '':
            self.horizontalSlider_2.setValue(int(self.lineEdit_4.text()))
    def res_y_te_update(self):
        if self.lineEdit_5.text() != '':
            self.horizontalSlider_3.setValue(int(self.lineEdit_5.text()))
    def skin_select(self):
        self.skin_, _ = QtWidgets.QFileDialog.getOpenFileName(None, 'Open File', './', "Image (*.png *.jpg *jpeg)")

    def render(self):
        try:
            # Создаем временный файл, чтобы избежать ошибки SameFileError
            import tempfile
            import shutil
            from PIL import Image

            # Создаем временную копию файла скина
            temp_dir = tempfile.gettempdir()
            temp_skin_path = os.path.join(temp_dir, "temp_skin.png")

            # Копируем оригинальный скин во временную папку, если пути разные
            if os.path.abspath(self.skin_) != os.path.abspath(temp_skin_path):
                shutil.copy(self.skin_, temp_skin_path)
            img = Image.open(temp_skin_path)
            if img.mode == 'P':
                rgba_skin = img.convert('RGBA')
                rgba_skin.save(temp_skin_path)
            # Загружаем скин и создаем перспективу
            skin = Skin.from_path(temp_skin_path)
            perspective = Perspective(
                x="right" if self.dir_left_right else 'left',
                y="front" if self.dir_front_back else 'back',
                z="up" if self.dir_up_down else 'down',
                scaling_factor=5
            )

            # Сохраняем рендер
            render_path = os.path.join(temp_dir, "render.png")
            skin.to_isometric_image(perspective).save(render_path)

            # Отображаем картинку в интерфейсе
            self.label_14.setPixmap(QtGui.QPixmap(render_path))

        except Exception as e:
            print(f"Ошибка при рендеринге скина: {e}")

    def left_right(self, value):
        self.dir_left_right = value
        if self.lang == 'en':
            self.label_15.setText("Right" if self.dir_left_right else 'Left')
        elif self.lang == 'ru':
            self.label_15.setText("Право" if self.dir_left_right else 'Лево')
        self.render()

    def front_back(self, value):
        self.dir_front_back = value
        if self.lang == 'en':
            self.label_16.setText("Front" if self.dir_front_back else 'Back')
        elif self.lang == 'ru':
            self.label_16.setText("Перед" if self.dir_front_back else 'Зад')  # Исправлено: было dir_left_right
        self.render()

    def up_down(self, value):
        self.dir_up_down = value
        if self.lang == 'en':
            self.label_17.setText("Up" if self.dir_up_down else 'Down')
        elif self.lang == 'ru':
            self.label_17.setText("Верх" if self.dir_up_down else 'Низ')  # Исправлено: было dir_left_right
        self.render()



import sys
app = QtWidgets.QApplication(sys.argv)
Form = QtWidgets.QWidget()
ui = Ui_Form()
ui.setupUi(Form)
Form.show()
sys.exit(app.exec_())