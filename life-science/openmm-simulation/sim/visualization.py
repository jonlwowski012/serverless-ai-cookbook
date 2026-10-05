"""
Visualization module for OpenMM simulation results.
Provides comprehensive plotting capabilities for molecular dynamics data.
"""

from pathlib import Path
from typing import List, Optional, Dict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import ListedColormap, BoundaryNorm

try:
    import mdtraj as md
    MDTRAJ_AVAILABLE = True
except ImportError:
    MDTRAJ_AVAILABLE = False
    print("Warning: MDTraj not available. Some visualizations will be limited.")

# Set matplotlib style for better-looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")


class SimulationVisualizer:
    """Comprehensive visualization class for OpenMM simulation results."""
    
    def __init__(self, sim_dir: Path, protein_id: str):
        """
        Initialize the visualizer.
        
        Args:
            sim_dir: Path to simulation directory
            protein_id: Protein identifier
        """
        self.sim_dir = sim_dir
        self.protein_id = protein_id
        self.trajectory_file = sim_dir / f"{protein_id}_trajectory.dcd"
        self.log_file = sim_dir / f"{protein_id}_simulation.log"
        self.simulation_topology_file = sim_dir / f"{protein_id}_simulation_topology.pdb"
        self.pdb_file = sim_dir / f"{protein_id}_processed.pdb"
        
        # Create plots directory
        self.plots_dir = sim_dir / "plots"
        self.plots_dir.mkdir(exist_ok=True)

    @staticmethod
    def _safe_tight_layout() -> None:
        """Apply tight layout but tolerate matplotlib recursion bugs on some Python versions."""
        try:
            plt.tight_layout()
        except RecursionError as e:
            print(f"Warning: Skipping tight_layout due to recursion error: {e}")
        except Exception as e:
            print(f"Warning: tight_layout failed: {e}")
        
    def parse_simulation_log(self) -> pd.DataFrame:
        """Parse the simulation log file into a pandas DataFrame."""
        if not self.log_file.exists():
            print(f"Warning: Log file {self.log_file} not found")
            return pd.DataFrame()
            
        try:
            # Read the log file and parse it
            data = []
            with open(self.log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Handle comma-separated values (CSV format)
                        if ',' in line:
                            parts = line.split(',')
                        else:
                            parts = line.split()
                        
                        if len(parts) >= 4:
                            try:
                                data.append({
                                    'Step': int(parts[0]),
                                    'Potential_Energy': float(parts[1]),
                                    'Temperature': float(parts[2]),
                                    'Speed': float(parts[3])
                                })
                            except (ValueError, IndexError) as e:
                                print(f"Warning: Skipping malformed line: {line} - {e}")
                                continue
            
            if data:
                df = pd.DataFrame(data)
                print(f"Successfully parsed {len(df)} data points from log file")
                return df
            else:
                print("No valid data found in log file")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error parsing log file: {e}")
            return pd.DataFrame()
    
    def load_trajectory(self) -> Optional[md.Trajectory]:
        """Load the MDTraj trajectory object."""
        if not MDTRAJ_AVAILABLE:
            print("MDTraj not available. Trajectory analysis disabled.")
            return None
            
        if not self.trajectory_file.exists():
            print(f"Warning: Trajectory file {self.trajectory_file} not found")
            return None
            
        try:
            # Try exact topology used in simulation first.
            if self.simulation_topology_file.exists():
                try:
                    return md.load(str(self.trajectory_file), top=str(self.simulation_topology_file))
                except Exception as e:
                    print(f"Failed to load trajectory with simulation topology: {e}")

            # Fallback to processed PDB if simulation topology is absent.
            if self.pdb_file.exists():
                try:
                    return md.load(str(self.trajectory_file), top=str(self.pdb_file))
                except Exception as e:
                    print(f"Failed to load trajectory with processed PDB: {e}")

            # Final fallback to original PDB.
            original_pdb = self.sim_dir / f"{self.protein_id}.pdb"
            if original_pdb.exists():
                try:
                    return md.load(str(self.trajectory_file), top=str(original_pdb))
                except Exception as e:
                    print(f"Failed to load trajectory with original PDB: {e}")

            print("No compatible topology found for trajectory analysis")
            return None
                
        except Exception as e:
            print(f"Error loading trajectory: {e}")
            return None
    
    def plot_energy_evolution(self, save_plot: bool = True) -> str:
        """Plot potential energy evolution over time."""
        df = self.parse_simulation_log()
        if df.empty:
            print("No simulation log data available for energy plot")
            return ""
            
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Energy plot
        ax1.plot(df['Step'], df['Potential_Energy'], 'b-', linewidth=1, alpha=0.7)
        ax1.set_ylabel('Potential Energy (kJ/mol)')
        ax1.set_title(f'Energy Evolution - {self.protein_id}')
        ax1.grid(True, alpha=0.3)
        
        # Temperature plot
        ax2.plot(df['Step'], df['Temperature'], 'r-', linewidth=1, alpha=0.7)
        ax2.set_xlabel('Simulation Step')
        ax2.set_ylabel('Temperature (K)')
        ax2.set_title('Temperature Evolution')
        ax2.grid(True, alpha=0.3)
        
        self._safe_tight_layout()
        
        if save_plot:
            plot_path = self.plots_dir / f"{self.protein_id}_energy_evolution.png"
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"Saved energy evolution plot to {plot_path}")
            return str(plot_path)
        else:
            plt.show()
            return ""
    
    def plot_rmsd_analysis(self, save_plot: bool = True) -> str:
        """Plot RMSD analysis if trajectory is available."""
        if not MDTRAJ_AVAILABLE:
            print("MDTraj not available for RMSD analysis")
            return ""
            
        traj = self.load_trajectory()
        if traj is None:
            print("Could not load trajectory for RMSD analysis")
            return ""
            
        try:
            # Calculate RMSD
            rmsd = md.rmsd(traj, traj, 0)
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # RMSD plot
            time_ns = traj.time / 1000  # Convert to nanoseconds
            ax1.plot(time_ns, rmsd, 'g-', linewidth=1, alpha=0.7)
            ax1.set_ylabel('RMSD (nm)')
            ax1.set_title(f'RMSD Analysis - {self.protein_id}')
            ax1.grid(True, alpha=0.3)
            
            # RMSD histogram
            ax2.hist(rmsd, bins=50, alpha=0.7, color='green', edgecolor='black')
            ax2.set_xlabel('RMSD (nm)')
            ax2.set_ylabel('Frequency')
            ax2.set_title('RMSD Distribution')
            ax2.grid(True, alpha=0.3)
            
            self._safe_tight_layout()
            
            if save_plot:
                plot_path = self.plots_dir / f"{self.protein_id}_rmsd_analysis.png"
                plt.savefig(plot_path, dpi=300, bbox_inches='tight')
                plt.close()
                print(f"Saved RMSD analysis plot to {plot_path}")
                return str(plot_path)
            else:
                plt.show()
                return ""
                
        except Exception as e:
            print(f"Error in RMSD analysis: {e}")
            return ""
    
    def plot_secondary_structure(self, save_plot: bool = True) -> str:
        """Plot secondary structure evolution if trajectory is available."""
        if not MDTRAJ_AVAILABLE:
            print("MDTraj not available for secondary structure analysis")
            return ""
            
        traj = self.load_trajectory()
        if traj is None:
            print("Could not load trajectory for secondary structure analysis")
            return ""
            
        try:
            # Calculate secondary structure
            dssp = md.compute_dssp(traj)
            
            # Create a heatmap of secondary structure
            fig, ax = plt.subplots(figsize=(15, 8))
            
            # Map DSSP codes to colors
            ss_colors = {
                'H': 'red',      # Alpha helix
                'B': 'orange',    # Beta bridge
                'E': 'yellow',    # Beta strand
                'G': 'pink',      # 3-10 helix
                'I': 'purple',    # Pi helix
                'T': 'blue',      # Turn
                'S': 'gray',      # Bend
                'C': 'white'      # Coil
            }
            
            # Use numeric codes (not object color arrays) for robust plotting.
            ss_order = list(ss_colors.keys())
            ss_to_idx = {ss: i for i, ss in enumerate(ss_order)}
            color_list = [ss_colors[ss] for ss in ss_order]
            default_idx = ss_to_idx["C"]

            numeric_matrix = np.full(dssp.shape, default_idx, dtype=np.int32)
            for i, frame in enumerate(dssp):
                for j, ss in enumerate(frame):
                    numeric_matrix[i, j] = ss_to_idx.get(ss, default_idx)

            cmap = ListedColormap(color_list)
            norm = BoundaryNorm(np.arange(len(ss_order) + 1) - 0.5, len(ss_order))

            # Plot heatmap
            ax.imshow(numeric_matrix, aspect='auto', cmap=cmap, norm=norm)
            ax.set_xlabel('Residue Number')
            ax.set_ylabel('Time Frame')
            ax.set_title(f'Secondary Structure Evolution - {self.protein_id}')
            
            # Add colorbar with custom labels
            from matplotlib.patches import Patch
            legend_elements = [Patch(facecolor=color, label=ss) 
                             for ss, color in ss_colors.items()]
            ax.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left')
            
            self._safe_tight_layout()
            
            if save_plot:
                plot_path = self.plots_dir / f"{self.protein_id}_secondary_structure.png"
                plt.savefig(plot_path, dpi=300, bbox_inches='tight')
                plt.close()
                print(f"Saved secondary structure plot to {plot_path}")
                return str(plot_path)
            else:
                plt.show()
                return ""
                
        except Exception as e:
            print(f"Error in secondary structure analysis: {e}")
            return ""
    
    def plot_simulation_summary(self, save_plot: bool = True) -> str:
        """Create a comprehensive summary plot."""
        df = self.parse_simulation_log()
        if df.empty:
            print("No simulation log data available for summary plot")
            return ""
            
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Energy evolution
        ax1.plot(df['Step'], df['Potential_Energy'], 'b-', alpha=0.7)
        ax1.set_title('Potential Energy')
        ax1.set_ylabel('Energy (kJ/mol)')
        ax1.grid(True, alpha=0.3)
        
        # Temperature evolution
        ax2.plot(df['Step'], df['Temperature'], 'r-', alpha=0.7)
        ax2.set_title('Temperature')
        ax2.set_ylabel('Temperature (K)')
        ax2.grid(True, alpha=0.3)
        
        # Speed evolution
        ax3.plot(df['Step'], df['Speed'], 'g-', alpha=0.7)
        ax3.set_title('Simulation Speed')
        ax3.set_xlabel('Step')
        ax3.set_ylabel('Speed (ns/day)')
        ax3.grid(True, alpha=0.3)
        
        # Energy histogram
        ax4.hist(df['Potential_Energy'], bins=30, alpha=0.7, color='blue', edgecolor='black')
        ax4.set_title('Energy Distribution')
        ax4.set_xlabel('Energy (kJ/mol)')
        ax4.set_ylabel('Frequency')
        ax4.grid(True, alpha=0.3)
        
        plt.suptitle(f'Simulation Summary - {self.protein_id}', fontsize=16)
        self._safe_tight_layout()
        
        if save_plot:
            plot_path = self.plots_dir / f"{self.protein_id}_summary.png"
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"Saved summary plot to {plot_path}")
            return str(plot_path)
        else:
            plt.show()
            return ""
    
    def create_additional_plots(self) -> List[str]:
        """Create additional matplotlib plots."""
        df = self.parse_simulation_log()
        if df.empty:
            print("No simulation log data available for additional plots")
            return []
            
        plot_paths = []
        
        # Energy vs Temperature scatter plot
        fig, ax = plt.subplots(figsize=(10, 6))
        scatter = ax.scatter(df['Temperature'], df['Potential_Energy'], 
                           c=df['Step'], cmap='viridis', alpha=0.7)
        ax.set_xlabel('Temperature (K)')
        ax.set_ylabel('Potential Energy (kJ/mol)')
        ax.set_title(f'Energy vs Temperature - {self.protein_id}')
        plt.colorbar(scatter, label='Simulation Step')
        plt.grid(True, alpha=0.3)
        
        plot_path = self.plots_dir / f"{self.protein_id}_energy_vs_temp.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        plot_paths.append(str(plot_path))
        print(f"Saved energy vs temperature plot to {plot_path}")
        
        # Speed evolution plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df['Step'], df['Speed'], 'g-', linewidth=2, alpha=0.7)
        ax.set_xlabel('Simulation Step')
        ax.set_ylabel('Speed (ns/day)')
        ax.set_title(f'Simulation Speed Evolution - {self.protein_id}')
        ax.grid(True, alpha=0.3)
        
        plot_path = self.plots_dir / f"{self.protein_id}_speed_evolution.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        plot_paths.append(str(plot_path))
        print(f"Saved speed evolution plot to {plot_path}")
        
        return plot_paths
    
    def generate_all_plots(self) -> Dict[str, str]:
        """Generate all available plots and return their paths."""
        plot_paths = {}
        
        print("Generating simulation visualizations...")
        
        # Basic plots (these should always work if log file exists)
        energy_plot = self.plot_energy_evolution()
        if energy_plot:
            plot_paths['energy_evolution'] = energy_plot
            
        summary_plot = self.plot_simulation_summary()
        if summary_plot:
            plot_paths['summary'] = summary_plot
            
        # Advanced plots (if MDTraj available and trajectory loads successfully)
        rmsd_plot = self.plot_rmsd_analysis()
        if rmsd_plot:
            plot_paths['rmsd_analysis'] = rmsd_plot
            
        ss_plot = self.plot_secondary_structure()
        if ss_plot:
            plot_paths['secondary_structure'] = ss_plot
            
        # Additional plots
        additional_plots = self.create_additional_plots()
        for i, plot_path in enumerate(additional_plots):
            plot_paths[f'additional_{i+1}'] = plot_path
            
        print(f"Generated {len(plot_paths)} visualization files")
        return plot_paths


def create_visualizations(sim_dir: Path, protein_id: str) -> Dict[str, str]:
    """
    Convenience function to create all visualizations for a simulation.
    
    Args:
        sim_dir: Path to simulation directory
        protein_id: Protein identifier
        
    Returns:
        Dictionary mapping plot names to file paths
    """
    print("="*50)
    print(f"Creating visualizations for {protein_id}")
    visualizer = SimulationVisualizer(sim_dir, protein_id)
    return visualizer.generate_all_plots() 