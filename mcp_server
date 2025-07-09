import json
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TypedDict, Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP
# from dp.agent.server import CalculationMCPServer

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# mcp = CalculationMCPServer("OpenFOAMCFDSimulator",host="0.0.0.0", port=50001)
mcp = FastMCP("OpenFOAMCFDSimulator", host="0.0.0.0",port=50001)

# --- Helper Functions ---

def _extract_boundary_names_from_polyMesh(case_path: Path) -> List[str]:
    """
    Extracts boundary names from the 'constant/polyMesh/boundary' file of an OpenFOAM case.

    Args:
        case_path (Path): The path to the OpenFOAM case directory.

    Returns:
        List[str]: A list of extracted boundary names. Returns an empty list if the file
                   does not exist or parsing fails.
    """
    boundary_file = case_path / "constant" / "polyMesh" / "boundary"
    if not boundary_file.exists():
        logging.warning(f"Boundary file not found: {boundary_file}")
        return []

    names = []
    try:
        with open(boundary_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Find the 'boundary' dictionary
            boundary_match = re.search(r"boundary\s*\{([^}]*)\}", content, re.DOTALL)
            if not boundary_match:
                logging.warning(f"Could not find 'boundary' section in {boundary_file}")
                return []

            boundary_section = boundary_match.group(1)
            # Find all names that precede an opening brace '{'
            name_matches = re.findall(r"^\s*([a-zA-Z0-9_]+)\s*\{", boundary_section, re.MULTILINE)
            names = [name.strip() for name in name_matches if name.strip()]
            logging.info(f"Extracted boundary names: {names}")
    except Exception as e:
        logging.error(f"Error extracting boundary names from {boundary_file}: {e}")
        return []
    return names

def _read_pdf_text(pdf_path: Path) -> str:
    """
    Simulates extracting text from a PDF file.
    In a real scenario, this would use a library like PyPDF2 or pdfplumber.
    This function is primarily for demonstrating ADK agent interaction and
    mocking its output for MCP tool testing.

    Args:
        pdf_path (Path): The path to the PDF file.

    Returns:
        str: A simulated text content from the PDF.
    """
    # Placeholder for actual PDF reading logic
    # from PyPDF2 import PdfReader
    # reader = PdfReader(pdf_path)
    # text = ""
    # for page in reader.pages:
    #     text += page.extract_text() or ""
    # return text

    logging.info(f"Simulating PDF text extraction from {pdf_path}")
    return f"""
    This paper presents a 2D steady-state incompressible flow simulation around a circular cylinder.
    The Reynolds number is 100.
    Inlet velocity boundary condition is applied at the left boundary.
    Outlet pressure boundary condition is applied at the right boundary.
    The top and bottom boundaries are symmetry planes.
    The cylinder surface is a no-slip wall.
    The domain has a specific mesh, typically starting from a .msh file.
    The simulation uses the SIMPLE algorithm.
    """

def _mock_llm_api_call(prompt: str, model_name: str) -> str:
    """
    Mocks an API call to an LLM, returning predefined JSON strings based on prompts.
    This function is intended for internal ADK agent use and testing, not directly by MCP tools.

    Args:
        prompt (str): The prompt sent to the LLM.
        model_name (str): The name of the LLM model.

    Returns:
        str: A JSON string representing the LLM's simulated response.
    """
    logging.debug(f"Mock LLM Call with model '{model_name}': {prompt[:100]}...")
    if "extract all the simulation conditions" in prompt:
        return json.dumps({
            "case_description": "这是一个关于圆柱绕流的二维稳态不可压缩流动仿真。雷诺数为100，速度入口，压力出口。",
            "solver": "simpleFoam",
            "turbulence_model": "laminar",
            "physical_model": "incompressible"
        })
    elif "boundary conditions (B.C.)" in prompt:
        return json.dumps({"inlet": "fixedValue", "outlet": "pressureOutlet", "cylinderWall": "noSlip", "frontAndBack": "empty", "topAndBottom": "symmetryPlane"})
    elif "initial and boundary conditions" in prompt:
        return json.dumps({
            "U": {"internalField": "[0 0 0]", "boundaryField": {"inlet": {"type": "fixedValue", "value": "uniform (1 0 0)"}, "outlet": {"type": "zeroGradient"}, "cylinderWall": {"type": "noSlip"}, "frontAndBack": {"type": "empty"}, "topAndBottom": {"type": "symmetryPlane"}}},
            "p": {"internalField": 0, "boundaryField": {"inlet": {"type": "zeroGradient"}, "outlet": {"type": "fixedValue", "value": "uniform 0"}, "cylinderWall": {"type": "zeroGradient"}, "frontAndBack": {"type": "empty"}, "topAndBottom": {"type": "symmetryPlane"}}}
        })
    elif "draft all the cases files" in prompt:
        return json.dumps({
            "system/controlDict": """FoamFile
{
    version       2.0;
    format        ascii;
    class         dictionary;
    object        controlDict;
}
application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1000;
deltaT          1;
writeControl    adjustableRunTime;
writeInterval   100;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;
""",
            "0/U": """FoamFile
{
    version       2.0;
    format        ascii;
    class         volVectorField;
    object        U;
}
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform (1 0 0);
    }
    outlet
    {
        type            zeroGradient;
    }
    cylinderWall
    {
        type            noSlip;
    }
    frontAndBack
    {
        type            empty;
    }
    topAndBottom
    {
        type            symmetryPlane;
    }
}
""",
            "0/p": """FoamFile
{
    version       2.0;
    format        ascii;
    class         volScalarField;
    object        p;
}
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    inlet
    {
        type            zeroGradient;
    }
    outlet
    {
        type            fixedValue;
        value           uniform 0;
    }
    cylinderWall
    {
        type            zeroGradient;
    }
    frontAndBack
    {
        type            empty;
    }
    topAndBottom
    {
        type            symmetryPlane;
    }
}
""",
            "system/fvSolution": """FoamFile
{
    version       2.0;
    format        ascii;
    class         dictionary;
    object        fvSolution;
}
solvers
{
    p
    {
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-06;
        relTol          0.01;
    }
    U
    {
        solver          PBiCG;
        preconditioner  DILU;
        tolerance       1e-05;
        relTol          0.1;
    }
}
PISO
{
    nCorrectors     2;
    nNonOrthogonalCorrectors 0;
    pRefCell        0;
    pRefValue       0;
}
""",
            "system/fvSchemes": """FoamFile
{
    version       2.0;
    format        ascii;
    class         dictionary;
    object        fvSchemes;
}
ddtSchemes
{
    default         Euler;
}
gradSchemes
{
    default         Gauss linear;
    grad(p)         Gauss linear;
}
divSchemes
{
    default         none;
    div(phi,U)      Gauss linearUpwindV;
    div(phi,k)      Gauss upwind;
    div(phi,epsilon) Gauss upwind;
}
laplacianSchemes
{
    default         Gauss linear corrected;
}
interpolationSchemes
{
    default         linear;
}
snGradSchemes
{
    default         corrected;
}
""",
            "constant/transportProperties": """FoamFile
{
    version       2.0;
    format        ascii;
    class         dictionary;
    object        transportProperties;
}
nu              nu [0 2 -1 0 0 0 0] 1e-06;
"""
        })
    return json.dumps({})



## MCP Tools Definition
### `ExtractSimulationConditions`

class SimulationConditionsResult(TypedDict):
    """Result structure for extract_simulation_conditions tool."""
    status: str
    message: str
    case_description: str
    solver: str
    turbulence_model: Optional[str]
    physical_model: Optional[str]

@mcp.tool()
def extract_simulation_conditions(
    llm_sim_conditions_json: str
) -> SimulationConditionsResult:
    """
    Parses a JSON string containing simulation conditions generated by a large language model
    and returns them in a structured format.

    Args:
        llm_sim_conditions_json (str): A JSON string from the LLM containing simulation conditions.

    Returns:
        SimulationConditionsResult: A dictionary containing the parsing status,
                                    a message, and the extracted simulation conditions.
    """
    try:
        sim_conditions = json.loads(llm_sim_conditions_json)

        required_keys = ["case_description", "solver"]
        if not all(key in sim_conditions for key in required_keys):
            logging.error(f"LLM simulation conditions JSON missing required keys: {sim_conditions}")
            return {
                "status": "failure",
                "message": f"LLM returned simulation conditions JSON is missing required keys or malformed: {sim_conditions}",
                "case_description": "", "solver": "", "turbulence_model": None, "physical_model": None
            }

        logging.info("Successfully parsed simulation conditions from LLM.")
        return {
            "status": "success",
            "message": "Simulation conditions parsed successfully.",
            "case_description": sim_conditions.get("case_description", ""),
            "solver": sim_conditions.get("solver", ""),
            "turbulence_model": sim_conditions.get("turbulence_model"),
            "physical_model": sim_conditions.get("physical_model")
        }
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON format for LLM simulation conditions: {e}. Original: {llm_sim_conditions_json[:500]}...")
        return {
            "status": "failure",
            "message": f"Input LLM JSON is malformed: {e}. Original response snippet: {llm_sim_conditions_json[:500]}...",
            "case_description": "", "solver": "", "turbulence_model": None, "physical_model": None
        }
    except Exception as e:
        logging.exception("An unexpected error occurred during simulation condition parsing.")
        return {
            "status": "failure",
            "message": f"An unexpected error occurred while parsing simulation conditions: {e}",
            "case_description": "", "solver": "", "turbulence_model": None, "physical_model": None
        }




### `ProcessMeshAndExtractBoundaries`

class MeshProcessResult(TypedDict):
    """Result structure for process_mesh_and_extract_boundaries tool."""
    status: str
    message: str
    case_output_path: Path
    boundary_names: List[str]

@mcp.tool()
def process_mesh_and_extract_boundaries(
    msh_file_path: Path,
    output_base_path: Path,
    case_name: str
) -> MeshProcessResult:
    """
    Converts a Fluent mesh file (.msh) to OpenFOAM format and extracts
    the boundary names from the converted mesh.

    Args:
        msh_file_path (Path): The path to the input Fluent mesh file.
        output_base_path (Path): The base directory where the OpenFOAM case will be created.
        case_name (str): The name of the OpenFOAM case directory to be created.

    Returns:
        MeshProcessResult: A dictionary containing the processing status,
                           a message, the path to the OpenFOAM case, and
                           a list of extracted boundary names.
    """
    case_output_path = output_base_path / case_name
    original_cwd = os.getcwd()

    try:
        case_output_path.mkdir(parents=True, exist_ok=True)
        logging.info(f"Created case directory: {case_output_path}")

        openfoam_path = os.environ.get("OPENFOAM_PATH")
        if not openfoam_path:
            logging.error("OPENFOAM_PATH environment variable is not set.")
            return {
                "status": "failure",
                "message": "OpenFOAM environment not initialized. OPENFOAM_PATH not found.",
                "case_output_path": Path(""), "boundary_names": []
            }

        os.chdir(case_output_path)
        logging.info(f"Changed current directory to: {case_output_path}")

        command = f'fluentMeshToFoam "{msh_file_path.resolve()}"'
        logging.info(f"Executing mesh conversion command: {command}")

        process = subprocess.run(
            command,
            shell=True,
            executable="/usr/bin/bash",
            capture_output=True,
            text=True,
            check=False,
            timeout=300 # Increased timeout for mesh conversion
        )

        if process.returncode != 0:
            logging.error(f"Mesh conversion failed. Stderr: {process.stderr}\nStdout: {process.stdout}")
            return {
                "status": "failure",
                "message": f"Mesh conversion failed: {process.stderr.strip()}",
                "case_output_path": case_output_path, "boundary_names": []
            }
        logging.info("Mesh conversion completed successfully.")
        logging.debug(f"fluentMeshToFoam Stdout: {process.stdout}")

        boundary_names = _extract_boundary_names_from_polyMesh(case_output_path)

        if not boundary_names:
            logging.warning("Mesh conversion successful, but no boundary names could be extracted.")
            return {
                "status": "failure",
                "message": "Mesh conversion successful, but failed to extract boundary names. Please check the mesh file structure.",
                "case_output_path": case_output_path, "boundary_names": []
            }

        logging.info("Mesh conversion and boundary name extraction successful.")
        return {
            "status": "success",
            "message": "Mesh conversion and boundary names extraction successful.",
            "case_output_path": case_output_path,
            "boundary_names": boundary_names
        }
    except subprocess.TimeoutExpired:
        logging.error(f"Mesh conversion timed out after {300} seconds for {msh_file_path}.")
        return {
            "status": "failure",
            "message": f"Mesh conversion timed out ({msh_file_path}).",
            "case_output_path": case_output_path, "boundary_names": []
        }
    except Exception as e:
        logging.exception(f"An unexpected error occurred during mesh processing for {msh_file_path}.")
        return {
            "status": "failure",
            "message": f"An unknown error occurred during mesh processing: {e}",
            "case_output_path": case_output_path, "boundary_names": []
        }
    finally:
        # Always change back to the original working directory
        if os.getcwd() != original_cwd:
            os.chdir(original_cwd)
            logging.info(f"Changed back to original directory: {original_cwd}")




class GeneratedFilesResult(TypedDict):
    """Result structure for generate_openfoam_case_files tool."""
    status: str
    message: str
    case_path: Path

@mcp.tool()
def generate_openfoam_case_files(
    case_path: Path,
    llm_boundary_types_json: str,  # This parameter appears to be unused in the current implementation.
                                   # Consider if it's truly needed or can be removed.
    llm_ic_bc_data_json: str,      # This parameter appears to be unused in the current implementation.
                                   # Consider if it's truly needed or can be removed.
    llm_case_files_content_json: str
) -> GeneratedFilesResult:
    """
    Receives OpenFOAM configuration file content generated by a large language model
    and writes these files to the specified case directory.

    Args:
        case_path (Path): The root path of the OpenFOAM case directory.
        llm_boundary_types_json (str): LLM-generated JSON for boundary types (currently unused).
        llm_ic_bc_data_json (str): LLM-generated JSON for initial/boundary condition data (currently unused).
        llm_case_files_content_json (str): LLM-generated JSON string where keys are
                                            relative file paths (e.g., "system/controlDict")
                                            and values are the file contents.

    Returns:
        GeneratedFilesResult: A dictionary containing the generation status,
                              a message, and the path to the case directory.
    """
    try:
        generated_files_content: Dict[str, str] = json.loads(llm_case_files_content_json)

        if not isinstance(generated_files_content, dict):
            raise ValueError("LLM returned file content is not a valid JSON dictionary.")

        logging.info(f"Writing {len(generated_files_content)} OpenFOAM case files to {case_path}...")
        for file_rel_path, content in generated_files_content.items():
            full_file_path = case_path / file_rel_path
            full_file_path.parent.mkdir(parents=True, exist_ok=True) # Ensure parent directories exist
            with open(full_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logging.debug(f"Wrote file: {full_file_path}")

        logging.info(f"Successfully generated and wrote case files to {case_path}.")
        return {
            "status": "success",
            "message": f"Case file content successfully generated and written to {case_path}.",
            "case_path": case_path
        }
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON format for LLM case files content: {e}. Original snippet: {llm_case_files_content_json[:500]}...")
        return {
            "status": "failure",
            "message": f"Input LLM JSON for case files is malformed: {e}. Please check the input JSON string. Original snippet: {llm_case_files_content_json[:500]}...",
            "case_path": case_path
        }
    except Exception as e:
        logging.exception(f"An unexpected error occurred while writing case files to {case_path}.")
        return {
            "status": "failure",
            "message": f"An error occurred while writing case files: {e}",
            "case_path": case_path
        }



### `RunOpenFOAMSimulation`

class SimulationResult(TypedDict):
    """Result structure for run_openfoam_simulation tool."""
    status: str
    message: str
    case_path: Path
    log_file_path: Path

@mcp.tool()
def run_openfoam_simulation(
    case_path: Path,
    solver_name: str,
    max_runtime_seconds: int = 600
) -> SimulationResult:
    """
    Executes an OpenFOAM solver for a specified case and captures the run log.

    Args:
        case_path (Path): The path to the OpenFOAM case directory.
        solver_name (str): The name of the OpenFOAM solver to run (e.g., 'simpleFoam').
        max_runtime_seconds (int): Maximum time in seconds to allow the solver to run
                                   before timing out. Defaults to 600 seconds (10 minutes).

    Returns:
        SimulationResult: A dictionary containing the simulation status, a message,
                          the path to the case, and the path to the log file.
    """
    log_file_path = case_path / "case_run.log"
    original_cwd = os.getcwd()

    try:
        if not case_path.is_dir():
            logging.error(f"Case path '{case_path}' does not exist or is not a directory.")
            return {
                "status": "failure",
                "message": f"Case path '{case_path}' does not exist or is not a directory.",
                "case_path": case_path, "log_file_path": Path("")
            }

        openfoam_path = os.environ.get("OPENFOAM_PATH")
        if not openfoam_path:
            logging.error("OPENFOAM_PATH environment variable is not set.")
            return {
                "status": "failure",
                "message": "OpenFOAM environment not initialized. OPENFOAM_PATH not found.",
                "case_path": case_path, "log_file_path": Path("")
            }

        # Clean up old time step directories to ensure a clean run
        for item in case_path.iterdir():
            # Matches directories named purely with numbers (e.g., '0', '100', '0.5')
            if item.is_dir() and re.match(r"^\d+(\.\d+)?$", item.name):
                logging.info(f"Cleaning up old time step directory: {item}")
                shutil.rmtree(item)

        os.chdir(case_path)
        logging.info(f"Changed current directory to: {case_path}")

        # Command to source OpenFOAM environment and run the solver
        command = f'source {openfoam_path}/etc/bashrc && {solver_name}'
        logging.info(f"Executing OpenFOAM solver command: {command}")

        with open(log_file_path, "w", encoding='utf-8') as log_f:
            process = subprocess.Popen(
                command,
                shell=True,
                executable="/usr/bin/bash",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Redirect stderr to stdout to capture all output in one log
                text=True,
                bufsize=1 # Line-buffered output
            )
            # Stream output to console and log file simultaneously
            for line in process.stdout:
                sys.stdout.write(line) # Print to console
                log_f.write(line)      # Write to log file
            process.stdout.close()
            process.wait(timeout=max_runtime_seconds) # Wait for process to complete or timeout

        if process.returncode == 0:
            logging.info(f"Solver '{solver_name}' ran successfully. Log saved to {log_file_path}.")
            return {
                "status": "success",
                "message": f"Solver '{solver_name}' ran successfully, log saved to {log_file_path}.",
                "case_path": case_path, "log_file_path": log_file_path
            }
        else:
            logging.error(f"Solver '{solver_name}' failed with exit code {process.returncode}. Log saved to {log_file_path}.")
            return {
                "status": "failure",
                "message": f"Solver '{solver_name}' failed, exit code: {process.returncode}, log saved to {log_file_path}.",
                "case_path": case_path, "log_file_path": log_file_path
            }
    except subprocess.TimeoutExpired:
        # If the process is still running, kill it
        if 'process' in locals() and process.poll() is None:
            process.kill()
            logging.warning(f"Killed timed-out solver process for '{solver_name}'.")
        logging.error(f"Solver '{solver_name}' timed out after {max_runtime_seconds} seconds. Log may be incomplete.")
        return {
            "status": "failure",
            "message": f"Solver '{solver_name}' timed out ({max_runtime_seconds} seconds). Log may be incomplete.",
            "case_path": case_path, "log_file_path": log_file_path
        }
    except Exception as e:
        logging.exception(f"An unexpected error occurred while running OpenFOAM simulation for {case_path}.")
        return {
            "status": "failure",
            "message": f"An unknown error occurred while running OpenFOAM case: {e}",
            "case_path": case_path, "log_file_path": log_file_path
        }
    finally:
        # Ensure we always change back to the original working directory
        if os.getcwd() != original_cwd:
            os.chdir(original_cwd)
            logging.info(f"Changed back to original directory: {original_cwd}")

if __name__ == "__main__":
    mcp.run(transport="sse")
