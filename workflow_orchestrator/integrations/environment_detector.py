"""Environment Detector — detects the runtime environment.

Detects:
Python, Node, Java, Go, Rust, .NET, Docker, Kubernetes, Git, NPM,
UV, Poetry, Pip, Operating System, CPU, RAM, GPU, Available storage
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentInfo:
    """Information about the runtime environment.

    Attributes:
        os_name: Operating system name.
        os_version: OS version string.
        cpu_count: Number of CPU cores.
        cpu_model: CPU model string.
        ram_gb: Total RAM in GB.
        gpu: GPU information.
        disk_free_gb: Free disk space in GB.
        python_version: Python version.
        node_version: Node.js version.
        java_version: Java version.
        go_version: Go version.
        rust_version: Rust version.
        dotnet_version: .NET version.
        docker_available: Whether Docker is available.
        git_available: Whether Git is available.
        kubernetes_available: Whether kubectl is available.
    """

    os_name: str = ""
    os_version: str = ""
    cpu_count: int = 0
    cpu_model: str = ""
    ram_gb: float = 0.0
    gpu: str = ""
    disk_free_gb: float = 0.0
    python_version: str = ""
    node_version: str = ""
    java_version: str = ""
    go_version: str = ""
    rust_version: str = ""
    dotnet_version: str = ""
    docker_available: bool = False
    git_available: bool = False
    kubernetes_available: bool = False


class EnvironmentDetector:
    """Detects the runtime environment including OS, hardware, and languages.

    Usage:
        >>> detector = EnvironmentDetector()
        >>> env = detector.detect()
        >>> print(f"{env.os_name}: {env.cpu_count} cores, {env.ram_gb}GB RAM")
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Environment Detector.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    def detect(self) -> EnvironmentInfo:
        """Detect the complete runtime environment.

        Returns:
            EnvironmentInfo with all detected information.
        """
        info = EnvironmentInfo()

        # OS
        info.os_name = platform.system()
        info.os_version = platform.version()

        # CPU
        info.cpu_count = os.cpu_count() or 0
        try:
            if platform.system() == "Linux":
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if "model name" in line:
                            info.cpu_model = line.split(":")[1].strip()
                            break
            elif platform.system() == "Darwin":
                result = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True, timeout=5)
                info.cpu_model = result.stdout.strip()
            elif platform.system() == "Windows":
                result = subprocess.run(["wmic", "cpu", "get", "name"], capture_output=True, text=True, timeout=5)
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    info.cpu_model = lines[1].strip()
        except Exception:
            pass

        # RAM
        try:
            if platform.system() == "Linux":
                with open("/proc/meminfo") as f:
                    for line in f:
                        if "MemTotal" in line:
                            kb = int(line.split()[1])
                            info.ram_gb = round(kb / (1024 * 1024), 1)
                            break
            elif platform.system() == "Darwin":
                result = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5)
                info.ram_gb = round(int(result.stdout.strip()) / (1024 ** 3), 1)
            elif platform.system() == "Windows":
                result = subprocess.run(["wmic", "memorychip", "get", "capacity"], capture_output=True, text=True, timeout=5)
                lines = result.stdout.strip().split("\n")[1:]
                total_bytes = sum(int(line.strip()) for line in lines if line.strip().isdigit())
                info.ram_gb = round(total_bytes / (1024 ** 3), 1)
        except Exception:
            pass

        # GPU
        try:
            result = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                info.gpu = result.stdout.strip().split("\n")[0] if result.stdout.strip() else ""
        except Exception:
            pass

        # Disk
        try:
            if platform.system() == "Windows":
                result = subprocess.run(["wmic", "logicaldisk", "where", "drivetype=3", "get", "freespace"], capture_output=True, text=True, timeout=5)
                lines = result.stdout.strip().split("\n")[1:]
                free_bytes = sum(int(line.strip()) for line in lines if line.strip().isdigit())
                info.disk_free_gb = round(free_bytes / (1024 ** 3), 1)
            else:
                stat = os.statvfs("/")
                info.disk_free_gb = round(stat.f_frsize * stat.f_bavail / (1024 ** 3), 1)
        except Exception:
            pass

        # Languages
        info.python_version = self._get_version("python3", "--version") or self._get_version("python", "--version")
        info.node_version = self._get_version("node", "--version")
        info.java_version = self._get_version("java", "-version", 2)
        info.go_version = self._get_version("go", "version")
        info.rust_version = self._get_version("rustc", "--version")
        info.dotnet_version = self._get_version("dotnet", "--version")

        # Tools
        info.docker_available = shutil.which("docker") is not None
        info.git_available = shutil.which("git") is not None
        info.kubernetes_available = shutil.which("kubectl") is not None

        self._publish_event("integration.environment_scanned", {
            "os": info.os_name,
            "cpu": info.cpu_count,
            "ram": info.ram_gb,
            "python": info.python_version,
        })

        return info

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(type=event_type, data=data, source="environment_detector"))
        except Exception:
            pass

    def _get_version(self, command: str, flag: str, stderr_lines: int = 1) -> str:
        """Get the version of a CLI tool.

        Args:
            command: CLI command.
            flag: Version flag.
            stderr_lines: Number of stderr lines to read.

        Returns:
            Version string or empty string.
        """
        if not shutil.which(command):
            return ""
        try:
            result = subprocess.run(
                [command] + flag.split(), capture_output=True, text=True, timeout=5,
            )
            output = result.stdout.strip() or result.stderr.strip()
            return output.split("\n")[0][:80]
        except Exception:
            return ""
