{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  # Packages required at runtime/build time

  buildInputs = with pkgs; [
    uv
    pyright
    sqlite
    cloudflared
  ];

  # Environment variables
  shellHook = ''
    echo "--- FastAPI & UV Development Environment ---"
    echo "UV version: $(uv --version)"

    export UV_PYTHON=3.11
    
    # Create a virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
      echo "Creating virtual environment..."
      uv venv
    fi

    # Activate the virtual environment automatically
    source .venv/bin/activate

    # Install dependencies from pyproject.toml
    echo "Syncing dependencies..."
    uv sync
  '';
}
