#!/usr/bin/python3
# Copyright (c) BDist Development Team
# Distributed under the terms of the Modified BSD License.
import os
from logging.config import dictConfig

from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from psycopg.rows import namedtuple_row
from psycopg_pool import ConnectionPool

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s:%(lineno)s - %(funcName)20s(): %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
    }
)

RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

app = Flask(__name__)
app.config.from_prefixed_env()
log = app.logger
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=RATELIMIT_STORAGE_URI,
)

# Use the DATABASE_URL environment variable if it exists, otherwise use the default.
# Use the format postgres://username:password@hostname/database_name to connect to the database.
DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://Aviacao:Aviacao@postgres/Aviacao")

pool = ConnectionPool(
    conninfo=DATABASE_URL,
    kwargs={
        "autocommit": True,  # If True don’t start transactions automatically.
        "row_factory": namedtuple_row,
    },
    min_size=4,
    max_size=10,
    open=True,
    # check=ConnectionPool.check_connection,
    name="postgres_pool",
    timeout=5,
)


def is_decimal(s):
    """Returns True if string is a parseable float number."""
    try:
        float(s)
        return True
    except ValueError:
        return False



"""----------------------- parte 1 do Exercicio 3 (TESTADA) --------------------------------"""
@app.route("/", methods=("GET",))
@app.route("/aeroporto", methods=("GET",))
@limiter.limit("1 por segundo")
def show_aeroportos():
    """Lista todos os aeroportos."""

    with pool.connection() as conn:
        with conn.cursor() as cur:
            aeroporto = cur.execute(
                """
                SELECT nome, cidade
                FROM aeroporto
                ORDER BY codigo DESC;
                """,
                {},
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")

    return jsonify(aeroporto), 200


"""----------------------- parte 2 do Exercicio 3 (TESTADA) --------------------------------"""
@app.route("/", methods=("GET",))
@app.route("/voos/<partida>", methods=("GET",))
@limiter.limit("1 per second")
def voos_por_partida(partida):
  
    """
    Lista todos os voos (número de série do avião e aeroporto de chegada)
    que partem do aeroporto de partida indicado até 12h após o momento da consulta.
    """
    agora = datetime.now()
    limite_tempo = agora + timedelta(hours=12)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT no_serie, hora_partida, chegada
                FROM voo
                WHERE partida = %(partida)s AND hora_partida BETWEEN %(agora)s AND %(limite_tempo)s;
                """,
                {
                    "partida": partida,
                    "agora": agora,
                    "limite_tempo": limite_tempo,
                },
            )
            voos = cur.fetchall()

    if not voos:
        return jsonify({"message": f"Nenhum voo encontrado com partida de {partida.upper()} nas próximas 12 horas.", "status": "info"}), 404

    return jsonify(voos), 200


"""----------------------- parte 3 do Exercicio 3 (TESTADA) --------------------------------"""
@app.route("/voos/<partida>/<chegada>", methods=("GET",))
@limiter.limit("1 per second")
def voos_disponiveis_view(partida, chegada):
    
    """Lista os próximos três voos com bilhetes disponíveis entre dois aeroportos."""

    with pool.connection() as conn:
        with conn.cursor() as cur:
            voos = cur.execute(
                """
                SELECT v.no_serie, v.hora_partida
                FROM voo v
                WHERE v.partida = %(partida)s AND v.chegada = %(chegada)s
                AND (
                    SELECT COUNT(*)
                    FROM assento a
                    LEFT JOIN bilhete b ON a.lugar = b.lugar AND a.no_serie = b.no_serie AND b.voo_id = v.id
                    WHERE a.no_serie = v.no_serie AND b.id IS NULL
                ) > 0
                ORDER BY v.hora_partida ASC
                LIMIT 3;
                """,
                {"partida": partida, "chegada": chegada},
            ).fetchall()
            log.debug(f"Found {cur.rowcount} rows.")

    if not voos:
        return jsonify({"message": "Não existem voos com bilhetes disponíveis.", "status": "error"}), 404

    return jsonify(voos), 200
  
   
"""----------------------- parte 4 do Exercicio 3 (TESTADA) --------------------------------"""
@app.route("/compra/<int:voo_id>", methods = ["POST"])
def compra_bilhetes(voo_id):
    request_data = request.json
    nif_client = request_data.get("nif")
    passageiros_data = request_data.get("passageiros", [])
    
    if not nif_client or not passageiros_data:
        return jsonify({"erro": "Dados em falta"}), 400
    
    try:
        with pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    
                    cur.execute("""INSERT INTO venda (nif_cliente, hora) VALUES (%s, %s, %s) RETURNING codigo_reserva;""", 
                                (nif_client, datetime.now()))
                    codigo_venda = cur.fetchone().codigo_reserva

                    for p in passageiros_data:
                        nome_passageiro_compra, classe_bilhete_compra = p["nome"], p["classe"]
                        cur.execute("""
                            SELECT lugar, no_serie
                            FROM assento
                            WHERE prim_classe = %(classe)s AND lugar NOT IN (
                                SELECT lugar FROM bilhete WHERE voo_id = %(voo)s AND lugar IS NOT NULL
                            )
                            AND no_serie = (SELECT no_serie FROM voo WHERE id = %(voo)s)
                            LIMIT 1;
                        """, {"classe": classe_bilhete_compra, "voo": voo_id})

                        lugar_data = cur.fetchone()
                        if not lugar_data:
                            return jsonify({"mensagem": "Sem lugares disponíveis na classe pedida"}), 404
    
                        if classe_bilhete_compra:
                            preco_bilhete = 300.0
                        else:
                            preco_bilhete = 150.0
    
                        cur.execute("""INSERT INTO bilhete (voo_id, codigo_reserva, nome_passegeiro, preco, prim_classe) VALUES (%s, %s, %s, %s, %s);""", 
                                    (voo_id, codigo_venda, nome_passageiro_compra, preco_bilhete, classe_bilhete_compra))

        return jsonify({"mensagem": "Bilhetes comprados com sucesso", "codigo_reserva": codigo_venda}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 400

  
"""-----------------------parte 5 do Exercicio 3 (TESTADA) --------------------------------"""
@app.route("/checkin/<int:bilhete_id>", methods=["POST"])
def checkin(bilhete_id):
    try:
        with pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    
                    cur.execute("""SELECT voo_id, prim_classe, no_serie FROM bilhete WHERE id = %s;""", (bilhete_id,))
                    bilhete_checkin = cur.fetchone()
                    if not bilhete_checkin:
                        return jsonify({"erro": "Bilhete não encontrado"}), 404
                   
                    cur.execute("""SELECT lugar FROM bilhete WHERE id = %s AND lugar IS NOT NULL;""", (bilhete_id,))
                    lugar_bilhete = cur.fetchone()
                    if lugar_bilhete:
                        return jsonify({"mensagem": "Bilhete já tem lugar atribuído"}), 200

                    cur.execute("""
                        SELECT lugar FROM assento
                        WHERE prim_classe = %s 
                          AND no_serie = (SELECT no_serie FROM voo WHERE id = %s)
                          AND lugar NOT IN (SELECT lugar FROM bilhete WHERE voo_id = %s AND lugar IS NOT NULL)
                        LIMIT 1;
                    """, (bilhete_checkin.prim_classe, bilhete_checkin.voo_id, bilhete_checkin.voo_id))
                    
                    assento = cur.fetchone()
                    if not assento:
                        return jsonify({"erro": "Sem lugares disponíveis"}), 400
                        
                    cur.execute("UPDATE bilhete SET lugar = %s WHERE id = %s;", (assento.lugar, bilhete_id))

        return jsonify({"mensagem": "Check-in realizado com sucesso", "lugar atribuído": assento.lugar}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 400

if __name__ == "__main__":
    app.run()
    