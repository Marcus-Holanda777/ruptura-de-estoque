from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from config import (
    ICON,
    IMG_RUP
)
from utils import main_ruptura
from pathlib import Path
from worker import Worker


class Ruptura(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dir_path = None
        self.threadpool = QThreadPool()
        
        # TODO: Configura DIALOGO
        self.setWindowTitle("Gera Ruptura")
        self.setWindowIcon(QIcon(ICON))
        self.setFixedSize(500, 350)
        
        # TODO: Definir style
        self.setStyleSheet("""
            QPushButton {
                background-color: lightgray;
            }
            QPushButton:hover {
                background-color: lightblue;
            }
            QProgressBar {
                text-align: center;
            }
        """)

        # TODO: Input caminho
        self.input = QLineEdit()
        self.input.setPlaceholderText("caminho do .access")
        self.input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input.setDisabled(True)
        
        # TODO: BTN - Listar arquivos
        self.btn_dir = QPushButton("LISTAR ACCESS")
        self.btn_dir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dir.clicked.connect(self.action_get_path)
        
        # TODO: Label de selecioar arquivo
        self.label = QLabel("- Selecionar tipo de saida do arquivo")
        self.combox = QComboBox()
        self.combox.addItems(['xlsx', 'csv', 'parquet'])
        
        # TODO: BTN - Gerar Relatorio dos Produtos
        self.btn = QPushButton("RUPTURA")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self.action_exec_ruptura)

        # TODO: Barra de progresso
        self.progress = QProgressBar(self)
        self.progress.setValue(0)

        # TODO: Logs
        self.logs = QLabel("...")
        self.logs.setAlignment(Qt.AlignmentFlag.AlignRight)

        # TODO: Adicionar IMAGEM
        img = QPixmap(IMG_RUP)
        self.lbl_img = QLabel()
        self.lbl_img.setPixmap(img)
        self.lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # TODO: Layout
        self.vlayout = QVBoxLayout()
        self.vlayout.addWidget(self.lbl_img)
        self.vlayout.addWidget(self.input)
        self.vlayout.addWidget(self.btn_dir)
        self.vlayout.addWidget(self.label)
        self.vlayout.addWidget(self.combox)
        self.vlayout.addWidget(self.btn)
        self.vlayout.addWidget(self.progress)
        self.vlayout.addWidget(self.logs)
        self.setLayout(self.vlayout)

    @Slot()
    def action_get_path(self):
        self.progress.setValue(0)

        path = QFileDialog.getExistingDirectory(
            self, 
            'Selecionar pasta', 
            dir='.',
            options=QFileDialog.Option.ShowDirsOnly
        )

        if path:
            self.input.setText(path)
            self.dir_path = list(Path(path).glob("**/*.accdb"))

            if not self.dir_path:
                QMessageBox.critical(
                    self,
                    "ERRO",
                    "Não existe arquivo (.accdb) !",
                    QMessageBox.StandardButton.Ok
                )
                self.dir_path = None
            else:
                QMessageBox.warning(
                    self,
                    "OK",
                    "Lista finalizada !",
                    QMessageBox.StandardButton.Ok
                )
        else:
            self.dir_path = None
    
    def update_progress(self, logs: tuple):
        value, name = logs
        self.progress.setValue(value)
        self.logs.setText(name)
    
    def worker_finished(self):
        QMessageBox.warning(
            self,
            "OK",
            "Finalizado com sucesso !",
            QMessageBox.StandardButton.Ok
        )
    
    def worker_error(self, error):
        self.progress.setStyleSheet("""
            QProgressBar {
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #FF0000;
            }"""
        )

        QMessageBox.critical(
            self,
            "ERROR",
            f"{error!r}",
            QMessageBox.StandardButton.Ok
        )
    
    @Slot()
    def action_exec_ruptura(self) -> None:
        if self.dir_path is None:
            QMessageBox.critical(
                self,
                "ERRO PATH",
                "Caminho não foi instanciado",
                QMessageBox.StandardButton.Ok
            )
            self.input.clear()

        else:
            self.progress.setMaximum(len(self.dir_path) + 1) 
            self.progress.setValue(0) 
            self.progress.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                }
            """
            )    
            worker = Worker(self.__export_ruptura)

            worker.signals.error.connect(self.worker_error)
            worker.signals.finished.connect(self.worker_finished)
            worker.signals.progress.connect(self.update_progress)
            
            self.threadpool.start(worker)

    def __export_ruptura(self, progress_callback) -> None:
        __ = main_ruptura(
            self.dir_path, 
            self.combox.currentText(), 
            progress_callback
        )