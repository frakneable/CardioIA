import json
import pathlib

DIR = pathlib.Path(__file__).resolve().parents[1] / "ir_alem_1"


def test_pastas_exigidas_pelo_enunciado():
    for pasta in ("contexts", "components", "services", "pages"):
        assert (DIR / "src" / pasta).is_dir()


def test_pacientes_json_coerente():
    pacientes = json.loads((DIR / "public" / "data" / "pacientes.json").read_text(encoding="utf-8"))
    assert len(pacientes) == 120
    assert len({p["id"] for p in pacientes}) == len({p["nome"] for p in pacientes}) == 120
    # O código 0 do UCI ("não medido") deve virar null, nunca aparecer como medida
    assert all(p["colesterol"] != 0 and p["pressaoSistolica"] != 0 for p in pacientes)


def test_build_e_dependencias_fora_do_git():
    ignorados = (DIR.parents[1] / ".gitignore").read_text(encoding="utf-8").split()
    assert "node_modules/" in ignorados and "dist/" in ignorados
