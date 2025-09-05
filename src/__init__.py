from contextlib import asynccontextmanager
import os
import asyncio
import logging
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from typing import Dict, List, Optional, Union
from pathlib import Path

from src import slicer
from src.config import Configuration
from src.designer import LedRange
from src.emergency_trap import EmergencyStop
from src.io import Io
from src.printer import Printer
from src.slicer.optimizer import optimize
from src.slicer.visualizer import visualize
from src.storage import Storage
from swarm import FtSwarm, MicrostepMode
from swarm.swarm import FtSwarmStepper

printer: Printer = None # type: ignore
storage: Storage = None # type: ignore
currently_printing_file: str | None = None
currently_printing_b64_image: str | None = None
moving_job = None
logger = logging.getLogger(__name__)
config = Configuration()
es: EmergencyStop = None # type: ignore

@asynccontextmanager
async def context(app: FastAPI):
    await initialize_app()
    yield

app = FastAPI(lifespan=context)

# Mount static files directory
app.mount("/static", StaticFiles(directory=Path(__file__).parent.parent / "static"), name="static")

# Create favicon route to prevent 404 errors
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(Path(__file__).parent.parent / "static" / "img" / "favicon.ico",
                       media_type="image/x-icon")

# Create a sub-application for API endpoints
from fastapi import APIRouter
api_router = APIRouter()

async def make_colorful(swarm: FtSwarm):
    outled = await LedRange("ftSwarm125.LED", 3, 5, swarm)
    printled = await LedRange("ftSwarm102.LED", 3, 10, swarm)
    while True:
        await asyncio.sleep(1)
        await outled.make_colorful("complementary")
        await printled.make_colorful("analogous")

async def initialize_app():
    global printer
    global storage
    global es

    swarm = FtSwarm("/dev/ttyUSB0")
    # swarm.logger.setLevel(logging.DEBUG)
    await swarm.set_microstep_mode("ftSwarm400", MicrostepMode.HALF)

    y_axis: FtSwarmStepper = await swarm._get_object(Io.PRINTER_Y, FtSwarmStepper)
    x_axis: FtSwarmStepper = await swarm._get_object(Io.PRINTER_X, FtSwarmStepper)
    tool0: FtSwarmStepper = await swarm._get_object(Io.TOOL0, FtSwarmStepper)
    tool1: FtSwarmStepper = await swarm._get_object(Io.TOOL1, FtSwarmStepper)
    es = await swarm._get_object(Io.EMERG, EmergencyStop)
    printer = Printer(swarm, x_axis, y_axis, [tool0, tool1], config, es)
    storage = await Storage(swarm, y_axis, es)
    #asyncio.create_task(make_colorful(swarm))

@api_router.get("/")
def read_root():
    if printer is None:
        return {"status": "initializing", "message": "Application is still initializing"}

    # Always include status information in the response
    response = {
        "status": "ready",
        "currently_printing_file": currently_printing_file,
        "moving_job": moving_job is not None
    }

    # Always include visualization status, but not the large image itself
    if currently_printing_b64_image:
        response["has_visualization"] = True
        # Include image length for debugging
        response["visualization_size"] = len(currently_printing_b64_image)
    else:
        response["has_visualization"] = False

    return response

@app.get("/", include_in_schema=False)
async def redirect_to_ui():
    """Redirect root path to UI"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/ui")

@app.get("/ui")
async def ui():
    """Serve the web UI"""
    return FileResponse(Path(__file__).parent.parent / "static" / "index.html")

@api_router.get("/files")
async def get_files() -> Dict[str, str]:
    """
    Returns all files from the printfiles directory with their content.

    This is an async endpoint to allow for non-blocking file reading.

    Returns:
        Dict[str, str]: Dictionary with filenames as keys and file content as values.
    """
    files_dict = {}
    printfiles_dir = Path(__file__).parent.parent / "printfiles"

    if not printfiles_dir.exists():
        logger.warning(f"Printfiles directory does not exist: {printfiles_dir}")
        return files_dict

    try:
        for file_path in printfiles_dir.iterdir():
            if file_path.is_file():
                try:
                    # Use async file reading for better performance
                    content = await asyncio.to_thread(file_path.read_text)
                    files_dict[file_path.name] = content
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {str(e)}")
                    files_dict[file_path.name] = f"Error reading file: {str(e)}"
    except Exception as e:
        logger.error(f"Error accessing directory {printfiles_dir}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error accessing files: {str(e)}")

    return files_dict

@api_router.post("/config/flowrate")
async def set_flow_rate(flow_rate: float = Query(..., ge=0.0, le=10.0)):
    """
    Update the flow rate in the configuration.

    Args:
        flow_rate: The new flow rate value (between 0.0 and 10.0)

    Returns:
        Dict with status and the updated flow rate
    """
    if flow_rate < 0.0 or flow_rate > 10.0:
        raise HTTPException(status_code=400, detail="Flow rate must be between 0.0 and 10.0")

    try:
        config.flow_rate = flow_rate
        config.save()
        logger.info(f"Flow rate updated to {flow_rate}")
        return {"status": "success", "flow_rate": flow_rate}
    except Exception as e:
        logger.error(f"Failed to update flow rate: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update flow rate: {str(e)}")

@api_router.get("/config/flowrate")
async def get_flow_rate():
    """
    Get the current flow rate from the configuration.

    Returns:
        Dict with the current flow rate
    """
    return {"flow_rate": config.flow_rate}

@api_router.get("/svg/{filename}")
async def get_svg(filename: str):
    """
    Returns an SVG file with the proper MIME type.

    Args:
        filename: Name of the SVG file to retrieve

    Returns:
        SVG content with the correct content type
    """
    printfiles_dir = Path(__file__).parent.parent / "printfiles"
    file_path = printfiles_dir / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

    if not filename.lower().endswith('.svg'):
        raise HTTPException(status_code=400, detail="Only SVG files are supported by this endpoint")

    try:
        content = file_path.read_text()
        return Response(content=content, media_type="image/svg+xml")
    except Exception as e:
        logger.error(f"Error reading SVG file {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

@api_router.get("/visualization")
async def get_visualization():
    """
    Returns the current visualization image if available.

    Returns:
        The visualization image with the correct content type or a 404 error
    """
    if not currently_printing_b64_image:
        raise HTTPException(status_code=404, detail="No visualization available")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Print Visualization</title>
        <style>
            body {{ font-family: sans-serif; margin: 0; padding: 20px; background: #f0f0f0; }}
            h1 {{ color: #333; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            img {{ max-width: 100%; border: 1px solid #ddd; }}
            .info {{ margin-top: 20px; padding: 10px; background: #f8f8f8; border-left: 3px solid #1a73e8; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Print Visualization</h1>
            <div class="info">
                <p>Showing visualization for: <strong>{currently_printing_file or "Most recent print"}</strong></p>
            </div>
            <img src="data:image/png;base64,{currently_printing_b64_image}" alt="Print visualization">
        </div>
    </body>
    </html>
    """
    return Response(content=html, media_type="text/html")

@api_router.get("/visualization/image")
async def get_visualization_image():
    """
    Returns just the visualization image as PNG if available.

    Returns:
        The raw PNG image with the correct content type or a 404 error
    """
    if not currently_printing_b64_image:
        raise HTTPException(status_code=404, detail="No visualization available")

    import base64
    try:
        # Decode the base64 string to binary
        image_binary = base64.b64decode(currently_printing_b64_image)
        return Response(content=image_binary, media_type="image/png")
    except Exception as e:
        logger.error(f"Error decoding visualization image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing visualization image: {str(e)}")

@api_router.get("/visualization/data")
async def get_visualization_data():
    """
    Returns just the base64 data for the visualization.

    Returns:
        JSON with the base64 encoded image or a 404 error
    """
    if not currently_printing_b64_image:
        raise HTTPException(status_code=404, detail="No visualization available")

    return {
        "image_data": currently_printing_b64_image,
        "filename": currently_printing_file,
    }

@api_router.post("/print")
async def print_file(file: str = Query(..., description="Filename to print")):
    """
    Endpoint to simulate printing a file.

    Args:
        file: Name of the file to print (from query parameter)

    Returns:
        Dict containing job information
    """
    global currently_printing_file

    if printer is None:
        raise HTTPException(status_code=503, detail="Print service is initializing")

    printfiles_dir = Path(__file__).parent.parent / "printfiles"
    file_path = printfiles_dir / file

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File '{file}' not found")

    if currently_printing_file is not None:
        raise HTTPException(status_code=409, detail="Already printing another file")
    # there are only SVGs
    async def do_print():
        global currently_printing_file
        global currently_printing_b64_image
        currently_printing_file = file
        logger.info(f"Starting print job for file: {file}")

        try:
            # Generate slicing and visualization
            logger.info(f"Slicing file: {file}")
            commands = optimize(slicer.slice("printfiles/" + file))

            logger.info(f"Generating visualization")
            currently_printing_b64_image = visualize(commands)
            logger.info(f"Visualization generated, size: {len(currently_printing_b64_image) if currently_printing_b64_image else 0} bytes")

            await printer.home()
            es.trap()

            for command in commands:
                await command.execute(printer)
                es.trap()

            logger.info(f"Completed print job for file: {file}")
        except Exception as e:
            logger.error(f"Error during print process: {str(e)}")
        finally:
            currently_printing_file = None
            # Keep the visualization image available even after printing completes
            logger.info("Visualization remains available at /api/visualization or /visualization")

    print_task = asyncio.create_task(do_print())

    # Wait just a moment to let the visualization start generating
    await asyncio.sleep(0.5)

    return {
        "status": "success",
        "message": f"Print job submitted for '{file}'",
        "file_type": "svg",
        "visualization_url": "/api/visualization/data",
        "visualization_status": "generating" if not currently_printing_b64_image else "ready"
    }

@api_router.get("/move")
async def move(amount: int = Query(..., description="amount"), speed: int = Query(..., description="speed"), type: str = Query(...)):
    typ = None
    if type == "tool0":
        typ = printer.tools[0]

    if type == "tool1":
        typ = printer.tools[1]

    if type == "tool2":
        typ = printer.tools[2]

    if type == "x":
        typ = printer.x_axis

    if type == "y":
        typ = printer.y_axis
    if typ == None:
        return "idk about this"
    await typ.set_speed(speed)
    await typ.set_distance(amount, True)
    await typ.run()


@api_router.post("/store")
async def store():
    async def do_store():
        await printer.home(False)
        await storage.from_printer_to_storage()
        global moving_job
        moving_job = None

    global moving_job
    if moving_job != None:
        return {"status": "error", "message": "Already moving"}
    moving_job = asyncio.create_task(do_store())
    return {"status": "success", "message": "Stored"}


@api_router.post("/storage/move/home_claw")
async def move_home():
    asyncio.create_task(storage.home_claw())

@api_router.post("/storage/move/x_next")
async def x_next():
    asyncio.create_task(storage.storage_x_axis.next())

@api_router.post("/storage/move/x_home")
async def x_home():
    asyncio.create_task(storage.storage_x_axis.home())

@api_router.post("/storage/move/y_home")
async def y_home():
    asyncio.create_task(storage.storage_y_axis.home())

@api_router.post("/storage/move/y_right")
async def y_right():
    asyncio.create_task(storage.storage_y_axis.goto(storage.storage_y_axis.POSITION_SEGMENT_RIGHT))

@api_router.post("/storage/move/rot_home")
async def rot_home():
    asyncio.create_task(storage.rotator.home())

@api_router.post("/storage/move/rot_act")
async def rot_act():
    asyncio.create_task(storage.rotator.action())

# Mount the API router at both / and /api paths
app.include_router(api_router)
app.include_router(api_router, prefix="/api")
