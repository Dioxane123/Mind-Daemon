#!/usr/bin/env python3
"""
Console output redirection utility for Mind Daemon.
Redirects stdout and stderr to files while optionally keeping terminal output.
"""

import sys
import os
from datetime import datetime
from typing import Optional, TextIO
from contextlib import contextmanager


class TeeFile:
    """A file-like object that writes to multiple streams."""
    
    def __init__(self, *files):
        self.files = files
    
    def write(self, text):
        for file in self.files:
            file.write(text)
            file.flush()
    
    def flush(self):
        for file in self.files:
            file.flush()


@contextmanager
def redirect_console_output(
    output_dir: str = "logs",
    log_prefix: str = "mind_daemon",
    keep_terminal: bool = True,
    include_timestamp: bool = True
):
    """
    Context manager to redirect console output to files.
    
    Args:
        output_dir: Directory to store log files
        log_prefix: Prefix for log files
        keep_terminal: Whether to continue showing output in terminal
        include_timestamp: Whether to include timestamp in filenames
    """
    # Create logs directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate log filenames
    if include_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stdout_file = os.path.join(output_dir, f"{log_prefix}_stdout_{timestamp}.log")
        stderr_file = os.path.join(output_dir, f"{log_prefix}_stderr_{timestamp}.log")
    else:
        stdout_file = os.path.join(output_dir, f"{log_prefix}_stdout.log")
        stderr_file = os.path.join(output_dir, f"{log_prefix}_stderr.log")
    
    # Open log files
    stdout_log = open(stdout_file, 'w', encoding='utf-8', buffering=1)
    stderr_log = open(stderr_file, 'w', encoding='utf-8', buffering=1)
    
    # Save original streams
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    try:
        # Set up tee streams
        if keep_terminal:
            sys.stdout = TeeFile(original_stdout, stdout_log)
            sys.stderr = TeeFile(original_stderr, stderr_log)
        else:
            sys.stdout = stdout_log
            sys.stderr = stderr_log
        
        print(f"📝 Console output redirected to:")
        print(f"   stdout: {stdout_file}")
        print(f"   stderr: {stderr_file}")
        print(f"   Terminal output: {'enabled' if keep_terminal else 'disabled'}")
        
        yield stdout_file, stderr_file
        
    finally:
        # Restore original streams
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        
        # Close log files
        stdout_log.close()
        stderr_log.close()
        
        print(f"📝 Log files saved:")
        print(f"   stdout: {stdout_file}")
        print(f"   stderr: {stderr_file}")


class LogRedirector:
    """Persistent log redirector that can be started and stopped."""
    
    def __init__(self, 
                 output_dir: str = "logs",
                 log_prefix: str = "mind_daemon",
                 keep_terminal: bool = True):
        self.output_dir = output_dir
        self.log_prefix = log_prefix
        self.keep_terminal = keep_terminal
        
        self.stdout_file: Optional[TextIO] = None
        self.stderr_file: Optional[TextIO] = None
        self.original_stdout: Optional[TextIO] = None
        self.original_stderr: Optional[TextIO] = None
        self.is_active = False
        
        self.stdout_path = ""
        self.stderr_path = ""
    
    def start(self) -> tuple[str, str]:
        """Start log redirection."""
        if self.is_active:
            print("⚠️ Log redirection is already active")
            return self.stdout_path, self.stderr_path
        
        # Create logs directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Generate log filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.stdout_path = os.path.join(self.output_dir, f"{self.log_prefix}_stdout_{timestamp}.log")
        self.stderr_path = os.path.join(self.output_dir, f"{self.log_prefix}_stderr_{timestamp}.log")
        
        # Open log files
        self.stdout_file = open(self.stdout_path, 'w', encoding='utf-8', buffering=1)
        self.stderr_file = open(self.stderr_path, 'w', encoding='utf-8', buffering=1)
        
        # Save original streams
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Set up tee streams
        if self.keep_terminal:
            sys.stdout = TeeFile(self.original_stdout, self.stdout_file)
            sys.stderr = TeeFile(self.original_stderr, self.stderr_file)
        else:
            sys.stdout = self.stdout_file
            sys.stderr = self.stderr_file
        
        self.is_active = True
        
        print(f"📝 Console logging started:")
        print(f"   stdout: {self.stdout_path}")
        print(f"   stderr: {self.stderr_path}")
        print(f"   Terminal output: {'enabled' if self.keep_terminal else 'disabled'}")
        
        return self.stdout_path, self.stderr_path
    
    def stop(self):
        """Stop log redirection and restore original streams."""
        if not self.is_active:
            print("⚠️ Log redirection is not active")
            return
        
        # Restore original streams
        if self.original_stdout:
            sys.stdout = self.original_stdout
        if self.original_stderr:
            sys.stderr = self.original_stderr
        
        # Close log files
        if self.stdout_file:
            self.stdout_file.close()
        if self.stderr_file:
            self.stderr_file.close()
        
        self.is_active = False
        
        print(f"📝 Console logging stopped. Files saved:")
        print(f"   stdout: {self.stdout_path}")
        print(f"   stderr: {self.stderr_path}")
    
    def get_log_paths(self) -> tuple[str, str]:
        """Get current log file paths."""
        return self.stdout_path, self.stderr_path


# Example usage
if __name__ == "__main__":
    # Test context manager
    print("Testing log redirection...")
    
    with redirect_console_output(output_dir="test_logs", log_prefix="test", keep_terminal=True):
        print("This should appear in both terminal and log file")
        print("Multiple lines of output", file=sys.stderr)
        print("Final test line")
    
    print("Back to normal terminal output")
    
    # Test persistent redirector
    print("\nTesting persistent redirector...")
    redirector = LogRedirector(output_dir="test_logs", log_prefix="persistent")
    
    stdout_path, stderr_path = redirector.start()
    print("This should be logged to file")
    print("Error message", file=sys.stderr)
    redirector.stop()
    
    print("Back to normal output")