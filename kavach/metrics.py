import platform
import time
from contextlib import contextmanager
from pathlib import Path

import psutil

from kavach.config import load_config


class StageTimer:
    def __init__(self):
        self.timings: dict[str, float] = {}

    @contextmanager
    def stage(self, name: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.timings[name] = self.timings.get(name, 0.0) + time.perf_counter() - t0

    @property
    def total(self) -> float:
        return sum(self.timings.values())


class EnergyMeter:
    """RAPL energy counter when readable (Linux); otherwise CPU utilisation x TDP x time, labelled estimated."""

    def __init__(self, rapl_path: Path | str | None = None, tdp_watts: float | None = None, cfg: dict | None = None):
        m = (cfg or load_config())["metrics"] if rapl_path is None or tdp_watts is None else {}
        self.rapl_path = Path(rapl_path or m["rapl_path"])
        self.tdp_watts = float(tdp_watts or m["cpu_tdp_watts"])

    def _read(self) -> int | None:
        try:
            return int(self.rapl_path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None

    def start(self) -> None:
        self._e0 = self._read()
        self._t0 = time.perf_counter()
        psutil.cpu_percent(interval=None)

    def stop(self) -> tuple[float, str]:
        seconds = time.perf_counter() - self._t0
        e1 = self._read()
        if self._e0 is not None and e1 is not None and e1 >= self._e0:
            return (e1 - self._e0) / 1e6, "measured"
        utilisation = psutil.cpu_percent(interval=None) / 100
        return utilisation * self.tdp_watts * seconds, "estimated"


def _cpu_name() -> str:
    try:
        if platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        if platform.system() == "Linux":
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def system_info() -> dict:
    return {
        "cpu": _cpu_name(),
        "physical_cores": psutil.cpu_count(logical=False) or 1,
        "logical_cores": psutil.cpu_count(logical=True) or 1,
        "ram_gb": round(psutil.virtual_memory().total / 1e9, 1),
        "os": f"{platform.system()} {platform.release()}",
    }
