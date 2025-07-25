#!/usr/bin/env python3
"""
MCP Services Launcher for Mind Daemon.
IMPORTANT: MCP servers are designed to be launched by MCP clients (like Claude Desktop).
This launcher is for development testing only - it will start servers but they will exit
when they detect no stdin input from an MCP client.

For production use, configure servers in Claude Desktop's config.json.
"""

import os
import sys
import subprocess
import time
import threading
from typing import List, Dict


class MCPServiceLauncher:
    """Launch and manage MCP services."""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.services = {
            "halo": {
                "script": "halo_server.py",
                "description": "Halo visual feedback control using exact halo.py implementation",
                "process": None
            },
            "music": {
                "script": "music_server.py", 
                "description": "Music playback control with mood/type support",
                "process": None
            },
            "bci-analysis": {
                "script": "analysis_server.py",
                "description": "BCI data analysis and monitoring",
                "process": None
            }
        }
        
    def launch_service(self, service_name: str) -> bool:
        """Launch a specific MCP service."""
        if service_name not in self.services:
            print(f"❌ Unknown service: {service_name}")
            return False
            
        service = self.services[service_name]
        script_path = os.path.join(self.base_dir, service["script"])
        
        if not os.path.exists(script_path):
            print(f"❌ Script not found: {script_path}")
            return False
            
        try:
            print(f"🚀 Launching {service_name}: {service['description']}")
            
            # Launch service process
            # CRITICAL FIX: Don't capture stdout/stderr to avoid pipe deadlock
            # Let services output directly to launcher's console for better debugging
            service["process"] = subprocess.Popen(
                [sys.executable, script_path],
                stdin=subprocess.PIPE, 
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            
            # Give it a moment to start (MCP servers need time to initialize)
            time.sleep(2)
            
            # Check if process is still running
            if service["process"].poll() is None:
                print(f"✅ {service_name} started successfully (PID: {service['process'].pid})")
                return True
            else:
                print(f"❌ {service_name} failed to start (process exited immediately)")
                print(f"   Check the service output above for error details")
                return False
                
        except Exception as e:
            print(f"❌ Error launching {service_name}: {e}")
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """Stop a specific MCP service."""
        if service_name not in self.services:
            print(f"❌ Unknown service: {service_name}")
            return False
            
        service = self.services[service_name]
        
        if service["process"] is None:
            print(f"⚠️ {service_name} is not running")
            return True
            
        try:
            service["process"].terminate()
            service["process"].wait(timeout=5)
            service["process"] = None
            print(f"⏹️ {service_name} stopped")
            return True
            
        except subprocess.TimeoutExpired:
            print(f"🔥 Force killing {service_name}")
            service["process"].kill()
            service["process"] = None
            return True
            
        except Exception as e:
            print(f"❌ Error stopping {service_name}: {e}")
            return False
    
    def launch_all(self) -> bool:
        """Launch all MCP services."""
        print("🚀 Launching all MCP services...")
        print("=" * 50)
        
        success_count = 0
        for service_name in self.services.keys():
            if self.launch_service(service_name):
                success_count += 1
            print()  # Add spacing
        
        print(f"📊 Services launched: {success_count}/{len(self.services)}")
        
        if success_count == len(self.services):
            print("✅ All services started successfully!")
            print("⚠️  Note: Services will exit soon due to no MCP client connection.")
            print("💡 For production use, configure these servers in Claude Desktop.")
            return True
        else:
            print("⚠️ Some services failed to start")
            return False
    
    def stop_all(self) -> bool:
        """Stop all MCP services."""
        print("⏹️ Stopping all MCP services...")
        
        for service_name in self.services.keys():
            self.stop_service(service_name)
        
        print("✅ All services stopped")
        return True
    
    def status(self) -> Dict:
        """Get status of all services."""
        status = {}
        
        for service_name, service in self.services.items():
            if service["process"] is None:
                status[service_name] = "stopped"
            elif service["process"].poll() is None:
                status[service_name] = "running"
            else:
                status[service_name] = "failed"
                service["process"] = None  # Clean up failed process
        
        return status
    
    def print_status(self):
        """Print status of all services."""
        print("📊 MCP Services Status:")
        print("=" * 30)
        
        status = self.status()
        for service_name, service_status in status.items():
            description = self.services[service_name]["description"]
            
            if service_status == "running":
                emoji = "✅"
            elif service_status == "stopped":
                emoji = "⏹️"
            else:
                emoji = "❌"
                
            print(f"{emoji} {service_name:15} - {description}")


def main():
    """Main launcher function."""
    launcher = MCPServiceLauncher()
    
    if len(sys.argv) < 2:
        print("🔧 MCP Services Launcher for Mind Daemon")
        print("=" * 40)
        print("Usage:")
        print("  python mcp_launcher.py <command>")
        print()
        print("Commands:")
        print("  start [service]  - Start all services or specific service")
        print("  stop [service]   - Stop all services or specific service")
        print("  status          - Show service status")
        print("  restart         - Restart all services")
        print()
        print("Available services:")
        for name, service in launcher.services.items():
            print(f"  • {name:15} - {service['description']}")
        return
    
    command = sys.argv[1].lower()
    
    if command == "start":
        if len(sys.argv) > 2:
            service_name = sys.argv[2]
            launcher.launch_service(service_name)
        else:
            launcher.launch_all()
            print("\n⚠️  Services will exit soon without MCP client connection.")
            print("💡 To use these servers, configure them in Claude Desktop's config.json.")
            print("💡 Use 'python mcp_launcher.py status' to check current status.")
            
    elif command == "stop":
        if len(sys.argv) > 2:
            service_name = sys.argv[2]
            launcher.stop_service(service_name)
        else:
            launcher.stop_all()
            
    elif command == "status":
        launcher.print_status()
        
    elif command == "restart":
        print("🔄 Restarting all MCP services...")
        launcher.stop_all()
        time.sleep(2)
        launcher.launch_all()
        
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'python mcp_launcher.py' for help")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)