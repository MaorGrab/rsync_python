import os
import subprocess


def recommend_worker_count() -> int:
    """Recommend optimal concurrent worker count for rsync transfers."""
    cpu_cores = _get_cpu_core_count()
    storage_type = _detect_storage_type()
    mem_gb = _get_total_memory_gb()
    workers = _calculate_base_workers(cpu_cores, storage_type)
    workers = _adjust_for_memory(workers, mem_gb)
    return min(workers, 16)  # Absolute cap

def _get_cpu_core_count() -> int:
    """Return available CPU core count with fallback."""
    return os.cpu_count() or 1

def _detect_storage_type() -> str:
    """Detect storage type (SSD/HDD) via sysfs rotational flag."""
    try:
        df_output = subprocess.check_output(
            "df / | tail -1 | awk '{print $1}'",
            shell=True, text=True
        ).strip()
        
        if df_output.startswith("/dev/"):
            device = df_output.split('/')[-1].rstrip('0123456789')
            rotational_path = f"/sys/block/{device}/queue/rotational"
            
            if os.path.exists(rotational_path):
                with open(rotational_path) as f:
                    return "hdd" if f.read().strip() == "1" else "ssd"
    except Exception:
        pass
    return "ssd"  # Default assumption

def _get_total_memory_gb() -> float:
    """Retrieve total system memory in gigabytes."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    mem_kb = int(line.split()[1])
                    return mem_kb / (1024 * 1024)
    except Exception:
        return 8.0  # Reasonable fallback value

def _calculate_base_workers(cpu_cores: int, storage_type: str) -> int:
    """Calculate base worker count based on CPU cores and storage type."""
    if storage_type == "ssd":
        return max(4, cpu_cores * 2)
    return max(2, cpu_cores)

def _adjust_for_memory(workers: int, mem_gb: float) -> int:
    """Reduce worker count if system memory is constrained."""
    if mem_gb < 2.0:
        return min(workers, 2)
    if mem_gb < 4.0:
        return min(workers, 4)
    return workers
