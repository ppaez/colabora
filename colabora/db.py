import sqlite3

from flask import g
from werkzeug.security import generate_password_hash
from .app import app


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(app.config["DATABASE"])
        db.execute('PRAGMA foreign_keys = ON')
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql') as f:
            db.executescript(f.read().decode())
        db.commit()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def a_dict(records):
    "Convierte lista de tuplas a diccionario anidado."
    d = {}
    for record in records:
        a, b, c, l = record
        d.setdefault(a, dict())
        d[a].setdefault(b, dict())
        d[a][b].setdefault(c, [])
        d[a][b][c].append(l)
    return d


def usuario_por_id(db, usuario_id):
    cmd = "SELECT * FROM usuarios WHERE usuario_id=?"
    cur = db.cursor()
    cur.execute(cmd, (usuario_id,))
    return cur.fetchone()


def usuario(db, usuario):
    cmd = "SELECT * FROM usuarios WHERE usuario=?"
    cur = db.cursor()
    cur.execute(cmd, (usuario,))
    return cur.fetchone()


def usuarios(db):
    """Regresa una lista de los usuarios

    Cada elemento es un diccionario con
    `usuario` y `rol`.
    """
    cmd = "SELECT * FROM usuarios"
    cur = db.cursor()
    cur.execute(cmd)
    records = cur.fetchall()
    return records


def areas(db):
    cmd = "SELECT nombre FROM areas"
    cur = db.cursor()
    cur.execute(cmd)
    records = cur.fetchall()
    return records

def areas_por_iniciativa(db):
    cmd = ("SELECT entidad.nombre, legislatura.nombre, numero, areas.nombre "
           "FROM clasificacion "
           "LEFT JOIN iniciativas USING (entidad_id, legislatura_id, numero) "
           "JOIN areas USING (area_id) "
           "JOIN entidad USING (entidad_id) "
           "JOIN legislatura USING (legislatura_id)")
    cur = db.cursor()
    cur.execute(cmd)
    records = cur.fetchall()
    return a_dict(records)


def asignadas_por_autor(db):
    cmd = ("SELECT usuario, count(numero) as asignadas FROM iniciativas "
           "LEFT JOIN asignacion USING (entidad_id, legislatura_id, numero) "
           "LEFT JOIN usuarios USING (usuario_id) "
           "GROUP BY usuario "
           "UNION "
           "SELECT usuario, count(numero) as asignadas FROM usuarios "
           "LEFT JOIN asignacion USING (usuario_id) "
           "LEFT JOIN iniciativas USING (entidad_id, legislatura_id, numero) "
           "GROUP BY usuario ")
    cur = db.cursor()
    cur.execute(cmd)
    records = cur.fetchall()
    return records

def iniciativa(db, entidad, legislatura, numero):
    cur = db.cursor()
    cmd = ("SELECT numero, cambios, tema, resumen, estado, comentario, usuario "
           "FROM iniciativas "
           "LEFT JOIN asignacion USING (entidad_id, legislatura_id, numero) "
           "LEFT JOIN usuarios USING (usuario_id) "
           "WHERE entidad_id=(SELECT entidad_id FROM entidad WHERE nombre=?) AND "
           "legislatura_id=(SELECT legislatura_id FROM legislatura WHERE nombre=?) AND "
           "numero=?")
    cur.execute(cmd, (entidad, legislatura, numero))
    record = cur.fetchone()
    return record

def iniciativas(db, entidad, legislatura, solo_sin_asignar=False):
    cmd = ("SELECT numero, cambios, tema, resumen, estado, comentario, usuario "
           "FROM iniciativas "
           "LEFT JOIN asignacion USING (entidad_id, legislatura_id, numero) "
           "LEFT JOIN usuarios USING (usuario_id) "
           "WHERE entidad_id=(SELECT entidad_id FROM entidad WHERE nombre=?) AND "
           "legislatura_id=(SELECT legislatura_id FROM legislatura WHERE nombre=?)")
    if solo_sin_asignar:
        cmd += " AND usuario ISNULL"
    cur = db.cursor()
    cur.execute(cmd,(entidad, legislatura))
    records = cur.fetchall()
    return records


def iniciativas_asignadas(db, entidad, legislatura, usuario):
    cmd = ("SELECT numero, cambios, tema, resumen, estado, comentario, usuario "
           "FROM iniciativas "
           "LEFT JOIN asignacion USING (entidad_id, legislatura_id, numero) "
           "LEFT JOIN usuarios USING (usuario_id) "
           "WHERE entidad_id=(SELECT entidad_id FROM entidad WHERE nombre=?) AND "
           "legislatura_id=(SELECT legislatura_id FROM legislatura WHERE nombre=?) AND "
           "usuario=?")
    cur = db.cursor()
    cur.execute(cmd, (entidad, legislatura, usuario))
    records = cur.fetchall()
    return records

def asigna(db, entidad, legislatura, numero, usuario):
    cmd = ("INSERT INTO asignacion (entidad_id, legislatura_id, numero, usuario_id) "
           "VALUES"
           "((SELECT entidad_id FROM entidad WHERE nombre=?), "
           "(SELECT legislatura_id FROM legislatura WHERE nombre=?), "
           "?, "
           "(SELECT usuario_id FROM usuarios WHERE usuario=?))")
    cur = db.cursor()
    try:
        cur.execute(cmd, (entidad, legislatura, numero, usuario))
        db. commit()
    except sqlite3.DatabaseError:
        return f"error: iniciativa {numero} no asignada a {usuario}"
    return f"ok: iniciativa {numero} asignada a {usuario}"


def clasifica(db, entidad, legislatura, numero, area):
    cmd = ("INSERT INTO clasificacion (entidad_id, legislatura_id, numero, area_id) "
           "VALUES"
           "((SELECT entidad_id FROM entidad WHERE nombre=?), "
           "(SELECT legislatura_id FROM legislatura WHERE nombre=?), "
           "?, "
           "(SELECT area_id FROM areas WHERE nombre=?))")
    cur = db.cursor()
    try:
        cur.execute(cmd, (entidad, legislatura, numero, area))
        db. commit()
    except sqlite3.DatabaseError:
        return f"error: iniciativa {numero} no asignada a {area}"
    return f"ok: iniciativa {numero} asignada a {area}"

def desclasifica(db, entidad, legislatura, numero):
    cmd = ("DELETE FROM clasificacion WHERE "
           "entidad_id=(SELECT entidad_id FROM entidad WHERE nombre=?) AND "
           "legislatura_id=(SELECT legislatura_id FROM legislatura WHERE nombre=?) AND "
           "numero=?")
    cur = db.cursor()
    cur.execute(cmd, (entidad, legislatura, numero))
    if cur.rowcount == 1:
        db. commit()
        return f"ok: se removieron areas de iniciativa {numero}"
    return f"error: no se removieron areas de iniciativa {numero}"

def agrega_iniciativa(db, entidad, legislatura, numero, cambios, tema, resumen,
                      comentario, estado):
    cmd = ("INSERT INTO iniciativas (entidad_id, legislatura_id, numero, "
           "cambios, tema, resumen, comentario, estado) "
           "VALUES "
           "((SELECT entidad_id FROM entidad WHERE nombre=?), "
           "(SELECT legislatura_id FROM legislatura WHERE nombre=?), "
           "?, ?, ?, ?, ?, ?)")
    cur = db.cursor()
    try:
        cur.execute(cmd, (entidad, legislatura, numero, cambios, tema, resumen,
                          comentario, estado))
        db.commit()
    except sqlite3.DatabaseError:
        return f"error: iniciativa {numero} no creada"
    return f"ok: iniciativa {numero} creada"


def agrega_area(db, nombre):
    cmd = "INSERT INTO areas (nombre) VALUES (?)"
    cur = db.cursor()
    try:
        cur.execute(cmd, (nombre,))
        db.commit()
    except sqlite3.DatabaseError:
        return f"error: '{nombre}' no creada"
    return f"ok: '{nombre}' creada"


def agrega_usuario(db, nombre, contrasena, rol):
    cmd = "INSERT INTO usuarios (usuario, contrasena, rol) VALUES (?, ?, ?)"
    cur = db.cursor()
    try:
        cur.execute(cmd, (nombre, generate_password_hash(contrasena), rol))
        db.commit()
    except sqlite3.DatabaseError:
        return f"error: '{nombre}' no creado"
    return f"ok: '{nombre}' creado"


def agrega_entidad(db, nombre):
    cmd = "INSERT INTO entidad (nombre) VALUES (?)"
    cur = db.cursor()
    try:
        cur.execute(cmd, (nombre,))
        db.commit()
    except sqlite3.DatabaseError:
        return f"error: '{nombre}' no creado"
    return f"ok: '{nombre}' creado"


def agrega_legislatura(db, nombre):
    cmd = "INSERT INTO legislatura (nombre) VALUES (?)"
    cur = db.cursor()
    try:
        cur.execute(cmd, (nombre,))
        db.commit()
    except sqlite3.DatabaseError:
        return f"error: '{nombre}' no creado"
    return f"ok: '{nombre}' creado"

def actualiza_iniciativa(db, entidad, legislatura, numero, tema=None, resumen=None,
                         comentario=None):
    fields = []
    values = []
    if tema:
        fields.append(f"tema=?")
        values.append(tema)
    if resumen:
        fields.append(f"resumen=?")
        values.append(resumen)
    if comentario:
        fields.append(f"comentario=?")
        values.append(comentario)
    sets = ', '.join(fields)
    if sets:
        cmd = (f"UPDATE iniciativas SET {sets} WHERE "
               "entidad_id=(SELECT entidad_id FROM entidad WHERE nombre=?) "
               "AND legislatura_id=(SELECT legislatura_id FROM legislatura WHERE nombre=?) "
               "AND numero=?")
        values.extend([entidad, legislatura, numero])
        cur = db.cursor()
        cur.execute(cmd, values)
        if cur.rowcount == 1:
            db.commit()
            return f"ok: iniciativa {numero} actualizada"
    return f"error: iniciativa {numero} no actualizada"
