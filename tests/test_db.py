import os
import tempfile

import pytest
from colabora.app import app as appli
from colabora.db import get_db, init_db
import colabora.db


with open(os.path.join(os.path.dirname(__file__), 'data.sql'), 'rb') as f:
    _data_sql = f.read().decode()


@pytest.fixture
def database():
    db_fd, db_path = tempfile.mkstemp()
    appli.config['DATABASE'] = db_path
    appli.testing = True
    with appli.app_context():
        init_db()
        db = get_db()
        yield db
    os.close(db_fd)
    os.unlink(db_path)


def test_a_dict():
    records = [
    (1, 10, 100, 1000),
    (1, 10, 100, 1001),
    (1, 11, 110, 1100),
    (2, 10, 100, 2100),
    ]
    result = colabora.db.a_dict(records)
    assert result == {1: {10: {100: [1000, 1001]},
                          11: {110: [1100]}
                          },
                      2: {10: {100: [2100]}
                          }
                      }


def test_usuarios(database):
    database.executescript(_data_sql)
    result = colabora.db.usuarios(database)
    assert len(result) == 2
    assert "usuario1" == result[0]["usuario"]


def test_areas(database):
    database.executescript(_data_sql)
    result = colabora.db.areas(database)
    assert len(result) == 1
    assert "area1" == result[0]["nombre"]


def test_asignadas_por_autor(database):
    database.executescript(_data_sql)
    result = colabora.db.asignadas_por_autor(database)
    assert len(result) == 1
    assert "usuario1" == result[0]["usuario"]
    assert 1 == result[0]["asignadas"]


def test_iniciativa_ok(database):
    database.executescript(_data_sql)
    result = colabora.db.iniciativa(database, estado='estado1' ,
                                    legislatura='legislatura1',
                                    numero=1)
    assert "tema1" == result['tema']

def test_iniciativa_none(database):
    database.executescript(_data_sql)
    result = colabora.db.iniciativa(database, estado='estado1',
                                    legislatura='legislatura1',
                                    numero=2)
    assert None == result


def test_iniciativas(database):
    database.executescript(_data_sql)
    result = colabora.db.iniciativas(database, estado='estado1',
                                     legislatura='legislatura1')
    assert len(result) == 1

def test_iniciativas_no_asignadas_vacio(database):
    database.executescript(_data_sql)
    result = colabora.db.iniciativas_asignadas(database, estado='estado1',
                                               legislatura='legislatura1',
                                               usuario='')
    assert len(result) == 0

def test_iniciativas_asignadas_ok(database):
    database.executescript(_data_sql)
    result = colabora.db.iniciativas_asignadas(database, estado='estado1',
                                               legislatura='legislatura1',
                                               usuario='usuario1')
    assert len(result) == 1
    assert 1 == result[0]["numero"]

def test_iniciativas_asignadas_vacio(database):
    database.executescript(_data_sql)
    result = colabora.db.iniciativas_asignadas(database, estado='estado1',
                                               legislatura='legislatura1',
                                               usuario='usuario2')
    assert len(result) == 0


def test_asigna_una(database):
    database.executescript(_data_sql)
    result = colabora.db.asigna(database, 'estado1', 'legislatura1', 1, 'usuario2')
    assert f"ok: iniciativa 1 asignada a usuario2" == result

def test_asigna_ninguna(database):
    database.executescript(_data_sql)
    result = colabora.db.asigna(database, 'estado1', 'legislatura1', 2, 'usuario1')
    assert f"error: iniciativa 2 no asignada a usuario1" == result


def test_agrega_iniciativa_ok(database):
    database.executescript(_data_sql)
    result = colabora.db.agrega_iniciativa(database, 'estado1', 'legislatura1', 2,
                                           'cambios', '', '', '', '')
    assert "ok: iniciativa 2 creada" == result

def test_agrega_iniciativa_error(database):
    database.executescript(_data_sql)
    result = colabora.db.agrega_iniciativa(database, 'estado1', 'legislatura1', 1,
                                           'cambios', '', '', '', '')
    assert "error: iniciativa 1 no creada" == result


def test_agrega_area_ok(database):
    result = colabora.db.agrega_area(database, 'area1')
    assert "ok: 'area1' creada" == result

def test_agrega_area_error(database):
    result = colabora.db.agrega_area(database, 'area1')
    result = colabora.db.agrega_area(database, 'area1')
    assert "error: 'area1' no creada" == result


def test_agrega_usuario_ok(database):
    result = colabora.db.agrega_usuario(database, 'usuario1')
    assert "ok: 'usuario1' creado" == result

def test_agrega_usuario_error(database):
    result = colabora.db.agrega_usuario(database, 'usuario1')
    result = colabora.db.agrega_usuario(database, 'usuario1')
    assert "error: 'usuario1' no creado" == result
