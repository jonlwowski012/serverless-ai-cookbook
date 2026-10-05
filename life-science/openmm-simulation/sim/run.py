"""Run a short molecular dynamics simulation and save its results."""

import argparse
import re

from openmm import app, unit

from .metadata import save_simulation_metadata
from .storage import upload_results_to_s3
from .utils import (
    clean_structure,
    create_simulation_directory,
    download_pdb,
    run_simulation_steps,
    setup_simulation,
)


def run_md_simulation(
    protein_id: str, steps: int, pdb_cache_dir: str | None, plots: bool
) -> None:
    sim_dir = create_simulation_directory(protein_id)
    pdb_file, pdb_source = download_pdb(protein_id, sim_dir, pdb_cache_dir)
    print(f"PDB source: {pdb_source}")
    topology, positions = clean_structure(pdb_file, protein_id, sim_dir)

    forcefield = app.ForceField("amber14-all.xml", "implicit/gbn2.xml")
    modeller = app.Modeller(topology, positions)
    modeller.addHydrogens(forcefield)
    with (sim_dir / f"{protein_id}_simulation_topology.pdb").open("w") as output:
        app.PDBFile.writeFile(modeller.topology, modeller.positions, output)

    system, integrator, simulation = setup_simulation(
        modeller.topology, modeller.positions, forcefield
    )
    simulation.context.setPositions(modeller.positions)
    print("Minimizing energy")
    simulation.minimizeEnergy(maxIterations=1000)
    simulation.context.setVelocitiesToTemperature(300 * unit.kelvin)
    trajectory = sim_dir / f"{protein_id}_trajectory.dcd"
    run_simulation_steps(
        simulation, steps, trajectory, sim_dir / f"{protein_id}_simulation.log"
    )
    save_simulation_metadata(
        protein_id, steps, sim_dir, system, integrator, simulation, str(trajectory)
    )

    if plots:
        from .visualization import create_visualizations

        create_visualizations(sim_dir, protein_id)
    upload_results_to_s3(sim_dir)
    print("Simulation complete!", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protein-id", default="1UBQ")
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--pdb-cache-dir")
    parser.add_argument(
        "--plots", action="store_true", help="Also generate trajectory plots"
    )
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9A-Za-z]{4}", args.protein_id) or args.steps < 1:
        parser.error("use a four-character PDB ID and a positive step count")
    run_md_simulation(
        args.protein_id.upper(), args.steps, args.pdb_cache_dir, args.plots
    )


if __name__ == "__main__":
    main()
