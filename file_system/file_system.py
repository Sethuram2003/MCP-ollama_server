from pathlib import Path
from typing import Optional
import os
import shutil
from datetime import datetime
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import sys
import io
from mcp.server.fastmcp import FastMCP, Context, Image
from mcp.server.fastmcp.prompts import base

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Create the MCP server
mcp = FastMCP("File Manager", dependencies=["python-magic"])

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Initialize any resources needed for the file manager"""
    # Could initialize database connections or other resources here
    yield {"initialized_at": datetime.now().isoformat()}

mcp = FastMCP("File Manager", lifespan=lifespan)

@mcp.resource("file://{path}")
def get_file_info(path: str) -> str:
    """Get information about a file or directory"""
    file_path = Path(path).expanduser().absolute()
    
    if not file_path.exists():
        return f"Path does not exist: {path}"
    
    if file_path.is_dir():
        contents = "\n".join(f.name for f in file_path.iterdir())
        return f"Directory: {path}\nContents:\n{contents}"
    else:
        stats = file_path.stat()
        return (
            f"File: {path}\n"
            f"Size: {stats.st_size} bytes\n"
            f"Last modified: {datetime.fromtimestamp(stats.st_mtime)}\n"
            f"Created: {datetime.fromtimestamp(stats.st_ctime)}"
        )

# Tool to create a new directory
@mcp.tool()
def create_directory(path: str, parents: bool = False) -> str:
    """Create a new directory at the specified path
    
    Args:
        path: The path where the directory should be created
        parents: If True, create parent directories as needed
    """
    dir_path = Path(path).expanduser().absolute()
    dir_path.mkdir(parents=parents, exist_ok=True)
    return f"Directory created at {dir_path}"

# Tool to create a new file
@mcp.tool()
def create_file(path: str, content: Optional[str] = None) -> str:
    """Create a new file at the specified path with optional content
    
    Args:
        path: The path where the file should be created
        content: Optional content to write to the file
    """
    file_path = Path(path).expanduser().absolute()
    file_path.touch()
    
    if content is not None:
        file_path.write_text(content)
        return f"File created at {path} with {len(content)} bytes of content"
    return f"Empty file created at {path}"

# Tool to write to a file
@mcp.tool()
def write_file(path: str, content: str, append: bool = False) -> str:
    """Write content to a file
    
    Args:
        path: Path to the file
        content: Content to write
        append: If True, append to the file instead of overwriting
    """
    file_path = Path(path).expanduser().absolute()
    
    if not file_path.exists():
        return f"Error: File does not exist at {path}"
    
    mode = "a" if append else "w"
    with file_path.open(mode) as f:
        f.write(content)
    
    action = "appended to" if append else "written to"
    return f"Content {action} {path} ({len(content)} bytes)"

# Tool to read a file
@mcp.tool()
def read_file(path: str) -> str:
    """Read the contents of a file
    
    Args:
        path: Path to the file
    """
    file_path = Path(path).expanduser().absolute()
    
    if not file_path.exists():
        return f"Error: File does not exist at {path}"
    
    if file_path.is_dir():
        return f"Error: {path} is a directory, not a file"
    
    return file_path.read_text()

# Tool to list directory contents
@mcp.tool()
def list_directory(path: str = ".", detailed: bool = False) -> str:
    """List contents of a directory
    
    Args:
        path: Path to the directory (defaults to current directory)
        detailed: If True, include detailed information
    """
    dir_path = Path(path).expanduser().absolute()
    
    if not dir_path.exists():
        return f"Error: Directory does not exist at {path}"
    
    if not dir_path.is_dir():
        return f"Error: {path} is not a directory"
    
    items = []
    for item in dir_path.iterdir():
        if detailed:
            stats = item.stat()
            items.append(
                f"{item.name}\n"
                f"  Type: {'Directory' if item.is_dir() else 'File'}\n"
                f"  Size: {stats.st_size} bytes\n"
                f"  Modified: {datetime.fromtimestamp(stats.st_mtime)}"
            )
        else:
            items.append(item.name)
    
    return f"Contents of {path}:\n" + "\n".join(items)

# Tool to delete a file or directory
@mcp.tool()
def delete_path(path: str, recursive: bool = False) -> str:
    """Delete a file or directory
    
    Args:
        path: Path to delete
        recursive: If True, delete directories recursively
    """
    target_path = Path(path).expanduser().absolute()
    
    if not target_path.exists():
        return f"Error: Path does not exist at {path}"
    
    if target_path.is_dir():
        if recursive:
            shutil.rmtree(target_path)
            return f"Directory {path} and all contents deleted"
        else:
            try:
                target_path.rmdir()
                return f"Directory {path} deleted"
            except OSError as e:
                return f"Error: Directory not empty. Use recursive=True to delete. {str(e)}"
    else:
        target_path.unlink()
        return f"File {path} deleted"

# Tool to move/rename a file or directory
@mcp.tool()
def move_path(source: str, destination: str) -> str:
    """Move or rename a file or directory
    
    Args:
        source: Current path
        destination: New path
    """
    src_path = Path(source).expanduser().absolute()
    dest_path = Path(destination).expanduser().absolute()
    
    if not src_path.exists():
        return f"Error: Source path does not exist at {source}"
    
    shutil.move(str(src_path), str(dest_path))
    return f"Moved {source} to {destination}"

# Tool to copy a file or directory
@mcp.tool()
def copy_path(source: str, destination: str) -> str:
    """Copy a file or directory
    
    Args:
        source: Path to copy from
        destination: Path to copy to
    """
    src_path = Path(source).expanduser().absolute()
    dest_path = Path(destination).expanduser().absolute()
    
    if not src_path.exists():
        return f"Error: Source path does not exist at {source}"
    
    if src_path.is_dir():
        shutil.copytree(str(src_path), str(dest_path))
    else:
        shutil.copy2(str(src_path), str(dest_path))
    
    return f"Copied {source} to {destination}"

# Tool to get current working directory
@mcp.tool()
def get_current_directory() -> str:
    """Get the current working directory"""
    return str(Path.cwd())

# Tool to change directory
@mcp.tool()
def change_directory(path: str) -> str:
    """Change the current working directory
    
    Args:
        path: Path to change to
    """
    new_path = Path(path).expanduser().absolute()
    
    if not new_path.exists():
        return f"Error: Path does not exist at {path}"
    
    if not new_path.is_dir():
        return f"Error: {path} is not a directory"
    
    os.chdir(str(new_path))
    return f"Changed working directory to {new_path}"

# Tool to get file metadata as an image (for previews)
@mcp.tool()
def get_file_preview(path: str) -> Optional[Image]:
    """Get a preview image of a file if possible
    
    Args:
        path: Path to the file
    """
    try:
        import magic
        from PIL import Image as PILImage
        
        file_path = Path(path).expanduser().absolute()
        
        if not file_path.exists() or file_path.is_dir():
            return None
            
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(str(file_path))
        
        if file_type.startswith('image/'):
            img = PILImage.open(str(file_path))
            img.thumbnail((300, 300))  # Create thumbnail
            return Image(data=img.tobytes(), format=img.format.lower())
    except ImportError:
        return None
    except Exception:
        return None
    
    return None

# Prompt for file operations
@mcp.prompt()
def file_operation_prompt(operation: str, target: str) -> list[base.Message]:
    """Prompt template for file operations"""
    return [
        base.UserMessage(f"I want to perform a file operation: {operation} on {target}"),
        base.AssistantMessage("I can help with that. What specific operation would you like to perform?"),
    ]

if __name__ == "__main__":
    mcp.run()