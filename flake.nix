{
  description = "研究室装置予約システム PoC 開発環境";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            # Backend
            python313
            uv
            ruff
            mypy
            python313Packages.pytest
            python313Packages.pytest-cov
            python313Packages.pytest-asyncio

            # Frontend
            nodejs_24

            # Tools（`just` はルート Justfile 用。依存コンテナ既定は Podman＝`podman-compose`）
            podman
            podman-compose
            just
          ];

          shellHook = ''
            export PYTHONPATH="$PWD/backend/src:$PYTHONPATH"
          '';
        };
      }
    );
}