import importlib.util as _ilu
import pathlib as _pl

_spec = _ilu.spec_from_file_location(
    "src.config._file",
    _pl.Path(__file__).parent.parent / "config.py",
)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# Re-export everything from config.py through the package
globals().update({k: v for k, v in vars(_mod).items() if not k.startswith("__")})
