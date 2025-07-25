class SSHConfig:
    def __init__(self,
                host: str = "172.20.10.2",
                port: int = 22,
                username: str = "root",
                password: str = "root",
                script_path: str = "/root/service_manager.sh",
                timeout: int = 30):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.script_path = script_path
        self.timeout = timeout
        
remote_config = SSHConfig()