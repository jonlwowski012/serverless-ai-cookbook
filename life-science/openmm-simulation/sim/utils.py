from datetime import datetime
import os
from pathlib import Path
import sys
import shutil
import urllib.request

from openmm import app, unit
import openmm as mm


def create_simulation_directory(protein_id: str) -> Path:
    """Create a timestamped directory for simulation results."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sim_dir = Path(f"results/{protein_id}_{timestamp}")
    sim_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created simulation directory: {sim_dir}")
    return sim_dir


def download_pdb(
    protein_id: str,
    sim_dir: Path,
    pdb_cache_dir: str | None = None,
) -> tuple[str, str]:
    """Resolve and return PDB file path plus source label.

    Args:
        protein_id: PDB identifier (e.g. ``1UBQ``).
        sim_dir: Directory where the resolved file will be placed.
        pdb_cache_dir: Explicit cache directory path.  Falls back to
            ``PDB_CACHE_DIR`` env var, then ``assets/pdb`` relative to
            the project root.
    """
    pdb_file = sim_dir / f"{protein_id}.pdb"

    if pdb_file.exists():
        return str(pdb_file), "results-cache"

    # Resolve cache directory: CLI arg > env var > default.
    project_root = Path(__file__).resolve().parents[1]
    default_cache_dir = project_root / "assets" / "pdb"

    raw_cache = (pdb_cache_dir or os.environ.get("PDB_CACHE_DIR", "")).strip()
    if raw_cache:
        resolved_cache = Path(raw_cache).expanduser()
        if not resolved_cache.is_absolute():
            resolved_cache = (project_root / resolved_cache).resolve()
    else:
        resolved_cache = default_cache_dir

    print(f"PDB cache directory: {resolved_cache}")
    cache_candidates = [
        resolved_cache / f"{protein_id}.pdb",
        resolved_cache / f"{protein_id.upper()}.pdb",
        resolved_cache / f"{protein_id.lower()}.pdb",
    ]
    for cached_pdb in cache_candidates:
        if cached_pdb.exists():
            shutil.copy2(cached_pdb, pdb_file)
            print(f"Copied cached PDB from {cached_pdb} to {pdb_file}")
            return str(pdb_file), f"local-cache:{cached_pdb}"

    url = f"https://files.rcsb.org/download/{protein_id}.pdb"
    print(f"Downloading {url}")
    urllib.request.urlretrieve(url, pdb_file)
    return str(pdb_file), f"remote:{url}"


def clean_structure(pdb_file: str, protein_id: str, sim_dir: Path):
    """Load PDB, remove water and non-protein residues."""

    print("Loading PDB structure...")
    pdb = app.PDBFile(pdb_file)

    # Create a modeller to clean up the structure
    modeller = app.Modeller(pdb.topology, pdb.positions)

    # Remove water molecules and other non-protein residues
    print("Removing water molecules and non-protein residues...")
    to_remove = []
    for residue in modeller.topology.residues():
        # Keep only standard amino acids
        if residue.name not in [
            "ALA",
            "ARG",
            "ASN",
            "ASP",
            "CYS",
            "GLU",
            "GLN",
            "GLY",
            "HIS",
            "ILE",
            "LEU",
            "LYS",
            "MET",
            "PHE",
            "PRO",
            "SER",
            "THR",
            "TRP",
            "TYR",
            "VAL",
        ]:
            to_remove.append(residue)

    if to_remove:
        print(f"Removing {len(to_remove)} non-protein residues...")
        modeller.delete(to_remove)

    # Save the processed structure
    processed_file = sim_dir / f"{protein_id}_processed.pdb"
    with open(processed_file, "w") as f:
        app.PDBFile.writeFile(modeller.topology, modeller.positions, f)
    print(f"Processed structure saved to {processed_file}")

    return modeller.topology, modeller.positions


def setup_simulation(topology, positions, forcefield):
    """Setup the OpenMM simulation system."""
    # Platform-specific optimizations
    if os.path.exists("/.dockerenv"):
        # Container optimizations
        os.environ["OPENMM_CPU_THREADS"] = "2"  # Limit CPU usage
        os.environ["OPENMM_DETERMINISTIC"] = "1"  # Use deterministic algorithms

    system = forcefield.createSystem(
        topology,
        nonbondedMethod=app.NoCutoff,
        constraints=app.HBonds,
    )
    integrator = mm.LangevinMiddleIntegrator(
        300 * unit.kelvin,
        1 / unit.picosecond,
        0.002 * unit.picoseconds,
    )
    # Cloud commands select CUDA; local examples select CPU. Fail if that
    # platform cannot initialize rather than silently using different hardware.
    platform_name = os.environ.get("OPENMM_PLATFORM", "CPU")
    platform = mm.Platform.getPlatformByName(platform_name)
    properties = {}
    if platform_name == "CUDA":
        properties["Precision"] = os.environ.get("OPENMM_PRECISION", "mixed")
        properties["DeviceIndex"] = os.environ.get("OPENMM_DEVICE_INDEX", "0")
    simulation = app.Simulation(topology, system, integrator, platform, properties)
    print(f"Using OpenMM platform: {platform_name}")

    return system, integrator, simulation


def run_simulation_steps(
    simulation, steps: int, output_filename: Path, log_filename: Path
):
    """Run the actual molecular dynamics simulation."""
    print(f"Running {steps} steps...")

    # Add reporters
    report_interval = max(1, steps // 10)
    simulation.reporters.append(app.DCDReporter(str(output_filename), report_interval))
    simulation.reporters.append(
        app.StateDataReporter(
            str(log_filename),
            report_interval,
            step=True,
            potentialEnergy=True,
            temperature=True,
            speed=True,
        )
    )
    simulation.reporters.append(
        app.StateDataReporter(
            sys.stdout,
            report_interval,
            step=True,
            potentialEnergy=True,
            temperature=True,
            speed=True,
        )
    )

    # Run simulation
    simulation.step(steps)
    print(f"Simulation completed. Output saved to {output_filename}")
