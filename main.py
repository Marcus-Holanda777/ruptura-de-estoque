from PySide6.QtCore import *       # not interfaces
from PySide6.QtWidgets import *    # widgets pronto para uso, ex: QPushButton
from PySide6.QtGui import *        # adiciona o CORE, como eventos
import sys
from config import (
    is_start_json,
    ICON,
    IMG
)
from dialog.login import Login
from dialog.produtos import Produtos
from dialog.ruptura import Ruptura


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Ruptura 1.0")
        self.setWindowIcon(QIcon(ICON))
        
        # TODO: Menu principal
        menu = self.menuBar().addMenu("&Menu")

        # TODO: Criando Acoes
        login_action = QAction(
            QIcon.fromTheme("system-log-out"), 
            "&Login", 
            self,
            triggered=self.show_dialog_login
        )
        
        # TODO: Criando Acoes
        prod_action = QAction(
            QIcon.fromTheme("document-save"), 
            "&Produtos", 
            self, 
            triggered=self.show_dialog_prod
        )

        ruptura_action = QAction(
            QIcon.fromTheme("document-revert"),
            "&Ruptura",
            self,
            triggered=self.show_dialog_ruptura
        )

        # TODO: Adicionar acoes ao MENU
        menu.addAction(login_action)
        menu.addAction(prod_action)
        menu.addAction(ruptura_action)

        # TODO: Adicionar IMAGEM
        img = QPixmap(IMG)
        self.lbl_img = QLabel()
        self.lbl_img.setPixmap(img)
        self.lbl_img.setAlignment(Qt.AlignCenter)

        self.setCentralWidget(self.lbl_img)
    
    def show_dialog_prod(self) -> None:
        if is_start_json():
            dialog = Produtos()
            dialog.exec()
        else:
            QMessageBox.critical(
                self,
                "ERROR",
                "Criar arquivo de LOGIN !",
                QMessageBox.StandardButton.Ok
            )
    
    def show_dialog_ruptura(self) -> None:
        dialog = Ruptura()
        dialog.exec()
    
    def show_dialog_login(self) -> None:
        dialog = Login()
        dialog.exec()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())