import os
import sys
import json
import time
import zipfile
import threading
import subprocess
import winreg
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as Item, Menu
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import send2trash

# Configuração e Lock de Acesso
config_lock = threading.Lock()
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extractor.log")

def log_message(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"
    print(log_line.strip())
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print(f"Erro ao escrever no log: {e}")

def get_downloads_folder():
    """Retorna o caminho da pasta Downloads lido do registro do Windows ou fallback."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
            # GUID padrão para pasta de Downloads
            download_path, _ = winreg.QueryValueEx(key, "{7D161CC2-B2F8-4370-9114-500E0877017F}")
            return os.path.expandvars(download_path)
    except Exception:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                # Fallback antigo do Windows
                download_path, _ = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
                return download_path
        except Exception:
            # Fallback final
            return os.path.join(os.path.expanduser('~'), 'Downloads')

class ZipHandler(FileSystemEventHandler):
    def __init__(self, processor):
        super().__init__()
        self.processor = processor

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.zip'):
            log_message(f"Arquivo ZIP criado: {event.src_path}")
            self.processor.process_file(event.src_path)

    def on_moved(self, event):
        # Muito importante para navegadores (Chrome/Edge/Firefox) que criam temp e renomeiam para .zip no final
        if not event.is_directory and event.dest_path.lower().endswith('.zip'):
            log_message(f"Arquivo renomeado para ZIP: {event.dest_path}")
            self.processor.process_file(event.dest_path)

class ZipAutoExtractorApp:
    def __init__(self):
        self.config = {}
        self.recent_extractions = []
        self.recent_lock = threading.Lock()
        
        self.load_config()
        self.resolve_paths()
        
        self.observer = None
        self.icon = None
        
        # Garante a pasta de assets
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        os.makedirs(assets_dir, exist_ok=True)
        self.icon_path = os.path.join(assets_dir, "icon.png")
        self.create_default_icon_if_missing()

    def load_config(self):
        with config_lock:
            try:
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                        self.config = json.load(f)
                else:
                    self.config = {
                        "monitored_folder": None,
                        "extraction_folder": None,
                        "extraction_mode": "subfolder",
                        "post_extraction_action": "recycle",
                        "backup_folder_name": "Zip_Backup",
                        "enabled": True
                    }
                    self.save_config_no_lock()
            except Exception as e:
                log_message(f"Erro ao carregar config: {e}")

    def save_config_no_lock(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            log_message(f"Erro ao salvar config: {e}")

    def save_config(self):
        with config_lock:
            self.save_config_no_lock()

    def resolve_paths(self):
        # Se monitorada for null, define como Downloads padrão
        if not self.config.get("monitored_folder"):
            self.config["monitored_folder"] = get_downloads_folder()
        
        # Se pasta de extração for null, define como a pasta monitorada
        if not self.config.get("extraction_folder"):
            self.config["extraction_folder"] = self.config["monitored_folder"]
            
        log_message(f"Pasta monitorada: {self.config['monitored_folder']}")
        log_message(f"Pasta de extração: {self.config['extraction_folder']}")

    def create_default_icon_if_missing(self):
        if not os.path.exists(self.icon_path):
            try:
                img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                
                # Desenha uma pasta azul escura moderna
                draw.rounded_rectangle([8, 16, 56, 52], radius=8, fill=(30, 41, 59, 255), outline=(59, 130, 246, 255), width=2)
                
                # Aba da pasta
                draw.polygon([(12, 16), (24, 16), (28, 22), (12, 22)], fill=(59, 130, 246, 255))
                
                # Seta amarela de extração apontando para baixo
                draw.rectangle([30, 24, 34, 38], fill=(245, 158, 11, 255))
                draw.polygon([(26, 38), (38, 38), (32, 46)], fill=(245, 158, 11, 255))
                
                img.save(self.icon_path, "PNG")
                log_message("Ícone padrão criado com sucesso.")
            except Exception as e:
                log_message(f"Erro ao gerar ícone: {e}")

    def get_icon_image(self):
        try:
            if os.path.exists(self.icon_path):
                return Image.open(self.icon_path)
        except Exception as e:
            log_message(f"Erro ao carregar imagem do ícone: {e}")
        
        # Último caso em memória
        img = Image.new('RGBA', (64, 64), (30, 41, 59, 255))
        return img

    def start_monitoring(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            
        if self.config.get("enabled"):
            folder = self.config.get("monitored_folder")
            if os.path.exists(folder):
                self.observer = Observer()
                self.observer.schedule(ZipHandler(self), folder, recursive=False)
                self.observer.start()
                log_message(f"Monitoramento iniciado na pasta: {folder}")
            else:
                log_message(f"Erro: Pasta monitorada não existe: {folder}")
                self.notify_user("Erro de Inicialização", f"A pasta monitorada não existe: {folder}")

    def stop_monitoring(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            log_message("Monitoramento parado.")

    def process_file(self, filepath):
        # Processa em uma thread para não bloquear a fila do Watchdog nem a UI do Tray
        threading.Thread(target=self._extract_thread, args=(filepath,), daemon=True).start()

    def _extract_thread(self, filepath):
        filename = os.path.basename(filepath)
        log_message(f"Iniciando tentativa de extração para: {filename}")
        
        # Espera o arquivo ser completamente liberado (download concluído)
        ready = False
        max_attempts = 120  # 60 segundos
        for i in range(max_attempts):
            if not os.path.exists(filepath):
                log_message(f"O arquivo {filename} desapareceu antes da extração.")
                return
            try:
                # Tenta abrir o arquivo para append de forma exclusiva
                with open(filepath, 'a'):
                    pass
                
                # Verifica estabilidade do tamanho
                size1 = os.path.getsize(filepath)
                time.sleep(0.5)
                size2 = os.path.getsize(filepath)
                
                if size1 == size2 and size1 > 0:
                    ready = True
                    break
            except IOError:
                # Arquivo bloqueado
                time.sleep(0.5)
        
        if not ready:
            log_message(f"Arquivo {filename} continuou bloqueado ou vazio após 60 segundos. Abortando.")
            self.notify_user("Falha na Extração", f"O download de {filename} parece não ter sido concluído.")
            return

        # Valida se é ZIP válido
        if not zipfile.is_zipfile(filepath):
            log_message(f"O arquivo {filename} não é um ZIP válido.")
            # Se for um arquivo de tamanho pequeno, pode ser erro temporário ou ZIP corrompido
            # Não notificaremos para evitar spam com outros arquivos temporários que não são ZIPs reais
            return

        try:
            monitored_dir = self.config["monitored_folder"]
            extraction_base = self.config["extraction_folder"]
            
            # Determina o diretório de destino
            if self.config["extraction_mode"] == "subfolder":
                # Nome do arquivo sem extensão
                folder_name = os.path.splitext(filename)[0]
                target_dir = os.path.join(extraction_base, folder_name)
                
                # Trata colisões criando pasta única
                counter = 1
                base_target = target_dir
                while os.path.exists(target_dir):
                    target_dir = f"{base_target} ({counter})"
                    counter += 1
            else:
                # Extração direta na raiz do diretório de extração
                target_dir = extraction_base
            
            os.makedirs(target_dir, exist_ok=True)
            
            log_message(f"Extraindo {filename} para {target_dir}...")
            
            # Realiza a extração
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
                
            log_message(f"Extração concluída com sucesso para: {target_dir}")
            self.add_to_history(target_dir)
            
            # Notifica o usuário
            self.notify_user("ZIP Extraído com Sucesso", f"{filename} foi extraído para:\n{os.path.basename(target_dir)}")
            
            # Ação pós-extração
            action = self.config.get("post_extraction_action", "keep")
            if action == "recycle":
                log_message(f"Movendo ZIP original para a Lixeira: {filename}")
                send2trash.send2trash(filepath)
            elif action == "delete":
                log_message(f"Excluindo ZIP original permanentemente: {filename}")
                os.remove(filepath)
            elif action == "backup":
                backup_dir = os.path.join(monitored_dir, self.config.get("backup_folder_name", "Zip_Backup"))
                os.makedirs(backup_dir, exist_ok=True)
                
                backup_path = os.path.join(backup_dir, filename)
                # Trata colisão na pasta de backup
                if os.path.exists(backup_path):
                    base_b, ext_b = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(os.path.join(backup_dir, f"{base_b} ({counter}){ext_b}")):
                        counter += 1
                    backup_path = os.path.join(backup_dir, f"{base_b} ({counter}){ext_b}")
                
                log_message(f"Movendo ZIP original para backup: {backup_path}")
                shutil.move(filepath, backup_path)
                
        except Exception as e:
            log_message(f"Erro durante a extração de {filename}: {e}")
            self.notify_user("Erro ao Extrair ZIP", f"Ocorreu um erro ao extrair {filename}:\n{str(e)}")

    def add_to_history(self, path):
        with self.recent_lock:
            # Evita duplicatas se o mesmo caminho for extraído
            if path in self.recent_extractions:
                self.recent_extractions.remove(path)
            self.recent_extractions.insert(0, path)
            # Mantém apenas os 5 mais recentes
            self.recent_extractions = self.recent_extractions[:5]
        
        # Atualiza o menu da bandeja para refletir o histórico
        self.update_menu()

    def notify_user(self, title, message):
        if self.icon:
            # O pystray permite enviar notificações nativas do Windows
            try:
                self.icon.notify(message, title)
            except Exception as e:
                log_message(f"Falha ao enviar notificação: {e}")

    # Ações do Menu
    def toggle_monitoring(self, icon, item):
        with config_lock:
            self.config["enabled"] = not self.config["enabled"]
            self.save_config_no_lock()
            
        enabled = self.config["enabled"]
        log_message(f"Chaveamento de monitoramento: habilitado = {enabled}")
        
        if enabled:
            self.start_monitoring()
            self.notify_user("Extrator Ativado", "Monitorando novos arquivos ZIP...")
        else:
            self.stop_monitoring()
            self.notify_user("Extrator Pausado", "Extração automática desativada.")
            
        self.update_menu()

    def set_extraction_mode(self, mode):
        def handler(icon, item):
            with config_lock:
                self.config["extraction_mode"] = mode
                self.save_config_no_lock()
            log_message(f"Modo de extração alterado para: {mode}")
            self.update_menu()
        return handler

    def set_post_action(self, action):
        def handler(icon, item):
            with config_lock:
                self.config["post_extraction_action"] = action
                self.save_config_no_lock()
            log_message(f"Ação pós-extração alterada para: {action}")
            self.update_menu()
        return handler

    def open_downloads(self, icon, item):
        folder = self.config.get("monitored_folder")
        if os.path.exists(folder):
            os.startfile(folder)
        else:
            log_message(f"Erro ao abrir Downloads, pasta não existe: {folder}")

    def open_extracted_folder(self, path):
        def handler(icon, item):
            if os.path.exists(path):
                os.startfile(path)
            else:
                self.notify_user("Pasta não encontrada", "A pasta extraída não existe mais ou foi movida.")
                with self.recent_lock:
                    if path in self.recent_extractions:
                        self.recent_extractions.remove(path)
                self.update_menu()
        return handler

    @property
    def is_startup_enabled(self):
        startup_dir = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
        shortcut_path = os.path.join(startup_dir, "ZipAutoExtract.lnk")
        return os.path.exists(shortcut_path)

    def toggle_startup(self, icon, item):
        state = not self.is_startup_enabled
        log_message(f"Alterando execução na inicialização para: {state}")
        
        startup_dir = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
        shortcut_path = os.path.join(startup_dir, "ZipAutoExtract.lnk")
        
        if state:
            try:
                target_path = sys.executable
                script_path = os.path.abspath(__file__)
                working_dir = os.path.dirname(script_path)
                
                # Se rodar como .pyw, sys.executable aponta para pythonw.exe ou python.exe
                # Se for python.exe, tenta mudar para pythonw.exe para rodar sem prompt
                if target_path.lower().endswith("python.exe"):
                    target_path = target_path[:-10] + "pythonw.exe"
                
                arguments = f'"{script_path}"'
                
                powershell_cmd = (
                    f'$WshShell = New-Object -ComObject WScript.Shell; '
                    f'$Shortcut = $WshShell.CreateShortcut("{shortcut_path}"); '
                    f'$Shortcut.TargetPath = "{target_path}"; '
                    f'$Shortcut.Arguments = \'{arguments}\'; '
                    f'$Shortcut.WorkingDirectory = "{working_dir}"; '
                    f'$Shortcut.Save()'
                )
                
                res = subprocess.run(["powershell", "-Command", powershell_cmd], capture_output=True, text=True, shell=True)
                if res.returncode == 0:
                    log_message("Atalho de inicialização criado com sucesso.")
                    self.notify_user("Inicialização Automática", "O extrator iniciará automaticamente com o Windows.")
                else:
                    log_message(f"Erro ao criar atalho de inicialização via PowerShell: {res.stderr}")
            except Exception as e:
                log_message(f"Falha ao configurar inicialização automática: {e}")
        else:
            try:
                if os.path.exists(shortcut_path):
                    os.remove(shortcut_path)
                log_message("Atalho de inicialização removido.")
                self.notify_user("Inicialização Automática", "O extrator não iniciará mais com o Windows.")
            except Exception as e:
                log_message(f"Falha ao remover atalho de inicialização: {e}")
                
        self.update_menu()

    def show_about(self, icon, item):
        # Exibe em uma thread separada para não bloquear o loop de mensagens da tray
        def _box():
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            messagebox.showinfo(
                "Sobre o ZipAutoExtract",
                "ZipAutoExtract v1.0\n\n"
                "Um utilitário elegante e automatizado para extrair arquivos ZIP "
                "assim que chegam na pasta Downloads.\n\n"
                "Desenvolvido sob medida.",
                parent=root
            )
            root.destroy()
        threading.Thread(target=_box, daemon=True).start()

    def quit_app(self, icon, item):
        log_message("Finalizando o aplicativo pelo menu da bandeja.")
        self.stop_monitoring()
        self.icon.stop()

    def create_menu(self):
        enabled = self.config.get("enabled", True)
        status_text = "Status: Monitorando" if enabled else "Status: Pausado"
        toggle_text = "Pausar Monitoramento" if enabled else "Retomar Monitoramento"
        
        mode = self.config.get("extraction_mode", "subfolder")
        action = self.config.get("post_extraction_action", "keep")
        
        # Constrói o submenu de Histórico
        with self.recent_lock:
            if not self.recent_extractions:
                history_menu = Menu(Item("Nenhuma extração recente", action=None, enabled=False))
            else:
                history_items = []
                for idx, path in enumerate(self.recent_extractions):
                    folder_name = os.path.basename(path)
                    # Corta nomes muito longos no menu
                    if len(folder_name) > 30:
                        folder_name = folder_name[:27] + "..."
                    history_items.append(Item(f"{idx+1}. {folder_name}", self.open_extracted_folder(path)))
                history_menu = Menu(*history_items)

        # Monta a estrutura de Menus
        return Menu(
            Item(status_text, action=None, enabled=False),
            Item(toggle_text, self.toggle_monitoring),
            Menu.SEPARATOR,
            Item("Pasta de Extração", Menu(
                Item("Subpasta com nome do ZIP (Recomendado)", self.set_extraction_mode("subfolder"), 
                     checked=lambda item: mode == "subfolder"),
                Item("Extrair na raiz (Downloads)", self.set_extraction_mode("direct"), 
                     checked=lambda item: mode == "direct")
            )),
            Item("Ação Pós-Extração", Menu(
                Item("Manter arquivo ZIP original", self.set_post_action("keep"), 
                     checked=lambda item: action == "keep"),
                Item("Mover ZIP para a Lixeira", self.set_post_action("recycle"), 
                     checked=lambda item: action == "recycle"),
                Item("Excluir ZIP permanentemente", self.set_post_action("delete"), 
                     checked=lambda item: action == "delete"),
                Item("Mover ZIP para subpasta Backup", self.set_post_action("backup"), 
                     checked=lambda item: action == "backup")
            )),
            Item("Histórico Recente", history_menu),
            Menu.SEPARATOR,
            Item("Abrir Pasta Downloads", self.open_downloads),
            Item("Executar na Inicialização", self.toggle_startup, 
                 checked=lambda item: self.is_startup_enabled),
            Item("Sobre o Extrator", self.show_about),
            Menu.SEPARATOR,
            Item("Sair", self.quit_app)
        )

    def update_menu(self):
        if self.icon:
            self.icon.menu = self.create_menu()

    def run(self):
        log_message("Iniciando aplicação ZipAutoExtract...")
        
        # Inicia monitor se ativado
        if self.config.get("enabled"):
            self.start_monitoring()
            
        # Cria e executa o ícone na área de notificação (esta chamada bloqueia)
        self.icon = pystray.Icon(
            "ZipAutoExtract",
            icon=self.get_icon_image(),
            title="ZipAutoExtract — Extrator de ZIP automático",
            menu=self.create_menu()
        )
        
        # Envia notificação inicial informando execução
        def notify_init():
            time.sleep(1) # Aguarda o tray estar pronto
            if self.config.get("enabled"):
                self.notify_user("ZipAutoExtract Ativo", "Monitorando a pasta Downloads para novos ZIPs.")
                
        threading.Thread(target=notify_init, daemon=True).start()
        
        self.icon.run()

if __name__ == "__main__":
    # Garante que só há uma instância rodando no Windows
    # Usamos um lock simples de arquivo para detecção de instância única
    lock_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.lock")
    try:
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except IOError:
                # Se não puder remover, significa que está bloqueado por outra instância rodando
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                messagebox.showwarning("ZipAutoExtract", "O Auto-Extrator já está rodando em segundo plano na barra de tarefas.")
                root.destroy()
                sys.exit(0)
                
        # Cria e segura o lock
        fh = open(lock_file, "w")
        fh.write("lock")
        fh.flush()
        
        app = ZipAutoExtractorApp()
        app.run()
        
        # Libera lock na saída
        try:
            fh.close()
            os.remove(lock_file)
        except Exception:
            pass
            
    except Exception as e:
        log_message(f"Falha crítica na execução: {e}")
        # Tenta remover o lock
        try:
            os.remove(lock_file)
        except Exception:
            pass
