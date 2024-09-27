from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *

from config import (
    read_start_json,
    is_start_json,
    init_start_json,
    ICON
)

class Login(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

         # TODO: Configura DIALOGO
        self.setWindowTitle("Login AWS")
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
        """)
        
        self.s3_staging_dir = QLineEdit()
        self.region_name = QComboBox()
        self.region_name.addItems(
            [
                 'us-east-1'
                ,'us-east-2'
                ,'ap-northeast-1'
                ,'ap-northeast-2'
                ,'ap-northeast-3'
                ,'ap-south-1'
                ,'ap-southeast-1'
                ,'ap-southeast-2'
                ,'ca-central-1'
                ,'eu-central-1'
                ,'eu-west-1'
                ,'eu-west-2'
                ,'eu-west-3'
                ,'sa-east-1'
                ,'us-west-1'
                ,'us-west-2'
                ,'cn-north-1'
                ,'cn-northwest-1'
            ]
        )
        self.aws_access_key_id = QLineEdit()
        self.aws_secret_access_key = QLineEdit()
        self.aws_secret_access_key.setEchoMode(QLineEdit.EchoMode.Password)

        self.init_load_json()
        
        # TODO: GRUPO Conexao
        self.group_s3 = QGroupBox("Connection")
        self.layout_group_s3 = QVBoxLayout()
        self.layout_group_s3.addWidget(QLabel("Region"))
        self.layout_group_s3.addWidget(self.region_name)
        self.layout_group_s3.addWidget(QLabel("S3 Location"))
        self.layout_group_s3.addWidget(self.s3_staging_dir)
        self.group_s3.setLayout(self.layout_group_s3)

        # TODO: GRUPO Conexao
        self.group_aut = QGroupBox("Autentication")
        self.layout_group_aut = QVBoxLayout()
        self.layout_group_aut.addWidget(QLabel("Nome usuario"))
        self.layout_group_aut.addWidget(self.aws_access_key_id)
        self.layout_group_aut.addWidget(QLabel("Senha"))
        self.layout_group_aut.addWidget(self.aws_secret_access_key)
        self.group_aut.setLayout(self.layout_group_aut)

        # TODO: BTN salvar
        self.btn_salvar = QPushButton("SALVAR")
        self.btn_salvar.clicked.connect(self.btn_action_salvar)
        self.btn_salvar.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.vlayout = QVBoxLayout()
        self.vlayout.addWidget(self.group_s3)
        self.vlayout.addWidget(self.group_aut)
        self.vlayout.addWidget(self.btn_salvar)
        self.setLayout(self.vlayout)
    
    def init_load_json(self) -> None:

        if is_start_json():
            data = read_start_json()
            for k, v in data.items():
                attr = getattr(self, k)

                if k == 'region_name':
                    attr.setCurrentText(v)
                else:
                    attr.setText(v)
    
    @Slot()
    def btn_action_salvar(self):
        try:
            if any(
                [
                    self.s3_staging_dir.text() == "",
                    self.aws_access_key_id.text() == "",
                    self.aws_secret_access_key.text() == "",
                    self.region_name.currentText() == ""
                ]
            ):
                
                raise ValueError("Valor não informado !")
        
            init_start_json(
                self.s3_staging_dir.text(),
                self.aws_access_key_id.text(),
                self.aws_secret_access_key.text(),
                self.region_name.currentText()
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "ERROR",
                f"{e}",
                QMessageBox.StandardButton.Ok
            )
        else:
            QMessageBox.warning(
                self,
                "OK",
                "Cadastrado com sucesso",
                QMessageBox.StandardButton.Ok
            )