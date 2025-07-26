import os
from dotenv import load_dotenv
load_dotenv()

class SSHConfig:
    def __init__(self,
                host: str = os.getenv('RDK_HOST'),
                port: int = 22,
                username: str = os.getenv('RDK_USER'),
                password: str = os.getenv('RDK_PASSWORD'),
                script_path: str = "/root/service_manager.sh",
                timeout: int = 30):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.script_path = script_path
        self.timeout = timeout
        
remote_config = SSHConfig()