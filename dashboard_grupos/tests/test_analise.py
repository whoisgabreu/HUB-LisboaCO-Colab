"""Testes das funções puras do dashboard (analise.py e nomes.py).

Executar da raiz do HUB:
    .venv/bin/python -m unittest dashboard_grupos.tests.test_analise
"""

import unittest
from datetime import datetime, timedelta

from dashboard_grupos import analise
from dashboard_grupos.nomes import limpar_nome_grupo


def msg(i, ts, tipo, grupo="G", nome="N", lid="L", texto="oi", papel=""):
    return {
        "id": i,
        "ts": ts,
        "tipo": tipo,
        "grupo": grupo,
        "nome": nome,
        "lid": lid,
        "texto": texto,
        "papel": papel,
        "data": ts.strftime("%Y-%m-%d"),
        "hora": ts.strftime("%H:%M:%S"),
        "group_lid": None,
    }


class TestNomes(unittest.TestCase):
    def test_remove_conectores_de_marca(self):
        self.assertEqual(limpar_nome_grupo("V4 Company & ATUS"), "ATUS")
        self.assertEqual(limpar_nome_grupo("ATUS & V4 Company"), "ATUS")
        self.assertEqual(limpar_nome_grupo("V4 Company + ATUS"), "ATUS")
        self.assertEqual(limpar_nome_grupo("ATUS + V4 Company"), "ATUS")

    def test_case_insensitive(self):
        self.assertEqual(limpar_nome_grupo("atus & v4 COMPANY"), "atus")
        self.assertEqual(limpar_nome_grupo("FLUA + v4  company"), "FLUA")

    def test_mantem_sem_marca_e_none(self):
        self.assertEqual(limpar_nome_grupo("Cliente X"), "Cliente X")
        self.assertEqual(limpar_nome_grupo("V4 Company"), "V4 Company")
        self.assertIsNone(limpar_nome_grupo(None))


class TestTempoUtil(unittest.TestCase):
    def test_dentro_do_horario(self):
        self.assertEqual(
            analise.tempo_util(datetime(2026, 10, 5, 17, 0), datetime(2026, 10, 5, 17, 30)),
            30.0,
        )

    def test_atravessa_fora_do_horario(self):
        # seg 17:30 -> 18:00 (30min) + ter 08:00 -> 08:30 (30min)
        self.assertEqual(
            analise.tempo_util(datetime(2026, 10, 5, 17, 30), datetime(2026, 10, 6, 8, 30)),
            60.0,
        )

    def test_fim_de_semana_nao_conta(self):
        # sábado 10:00 -> 11:00
        self.assertEqual(
            analise.tempo_util(datetime(2026, 10, 3, 10, 0), datetime(2026, 10, 3, 11, 0)),
            0.0,
        )


class TestPercentil(unittest.TestCase):
    def test_percentis(self):
        self.assertEqual(analise._percentil([1, 2, 3, 4], 50), 2.5)
        self.assertEqual(analise._percentil([1, 2, 3, 4], 0), 1)
        self.assertEqual(analise._percentil([1, 2, 3, 4], 100), 4)
        self.assertIsNone(analise._percentil([], 50))


class TestStatusGrupos(unittest.TestCase):
    def test_nunca_ativo_e_ativo(self):
        reg = [{"name": "G1", "lid": "l1"}, {"name": "G2", "lid": "l2"}]
        msgs = [
            msg(1, datetime(2026, 10, 10, 11, 0), "equipe", "G1", nome="A"),
            msg(2, datetime(2026, 10, 10, 11, 5), "cliente", "G1", nome="B"),
        ]
        out = {s["nome"]: s for s in analise.status_grupos(msgs, reg, 3)}
        self.assertEqual(out["G2"]["status"], "nunca")
        self.assertEqual(out["G1"]["status"], "ativo")

    def test_inativo(self):
        reg = [{"name": "G1", "lid": "l1"}, {"name": "G2", "lid": "l2"}]
        msgs = [
            msg(1, datetime(2026, 10, 1, 11, 0), "equipe", "G1"),
            msg(2, datetime(2026, 10, 10, 11, 0), "equipe", "G2"),
            msg(3, datetime(2026, 10, 10, 11, 5), "cliente", "G2"),
        ]
        out = {s["nome"]: s for s in analise.status_grupos(msgs, reg, 3)}
        self.assertEqual(out["G1"]["status"], "inativo")
        self.assertEqual(out["G2"]["status"], "ativo")

    def test_semi_cliente(self):
        reg = [{"name": "G1", "lid": "l1"}]
        msgs = [msg(1, datetime(2026, 10, 10, 11, 0), "equipe", "G1")]
        out = {s["nome"]: s for s in analise.status_grupos(msgs, reg, 3)}
        self.assertEqual(out["G1"]["status"], "semi_cliente")


class TestClientesInativos(unittest.TestCase):
    def test_detecta_quem_nunca_respondeu(self):
        msgs = [
            msg(1, datetime(2026, 10, 1, 9, 0), "cliente", "G", nome="Antes", lid="L1"),
            msg(2, datetime(2026, 10, 1, 10, 0), "equipe", "G", nome="Eq", lid="LE"),
            msg(3, datetime(2026, 10, 1, 11, 0), "cliente", "G", nome="Depois", lid="L2"),
        ]
        nomes = [c["nome"] for c in analise.clientes_inativos(msgs)]
        self.assertIn("Antes", nomes)
        self.assertNotIn("Depois", nomes)


class TestResumoSerie(unittest.TestCase):
    def test_resumo_geral(self):
        msgs = [
            msg(1, datetime(2026, 10, 1, 9, 0), "equipe", "G1", lid="L1"),
            msg(2, datetime(2026, 10, 1, 10, 0), "cliente", "G1", lid="L2"),
            msg(3, datetime(2026, 10, 2, 9, 0), "equipe", "G2", lid="L1"),
        ]
        r = analise.resumo_geral(msgs)
        self.assertEqual(r["total"], 3)
        self.assertEqual(r["remetentes"], 2)
        self.assertEqual(r["grupos"], 2)
        self.assertEqual(r["msgs_equipe"], 2)
        self.assertEqual(r["msgs_cliente"], 1)
        self.assertEqual(r["dias"], 2)

    def test_serie_dia(self):
        msgs = [
            msg(1, datetime(2026, 10, 1, 9, 0), "equipe"),
            msg(2, datetime(2026, 10, 1, 10, 0), "cliente"),
            msg(3, datetime(2026, 10, 2, 9, 0), "equipe"),
        ]
        self.assertEqual(analise.serie(msgs, "dia"), [["2026-10-01", 2], ["2026-10-02", 1]])


class TestSlaPorDiaSemana(unittest.TestCase):
    def test_media_por_dia(self):
        msgs = [
            msg(1, datetime(2026, 10, 5, 9, 0), "cliente", "G", nome="C"),
            msg(2, datetime(2026, 10, 5, 9, 30), "equipe", "G", nome="E"),
        ]
        r = analise.sla_por_dia_semana(msgs, "cliente", "equipe")
        self.assertEqual(r[0], ["Seg", 30.0, 1])
        self.assertEqual(r[5][0], "Sáb")
        self.assertIsNone(r[5][1])


class TestClientesEmRisco(unittest.TestCase):
    def test_detecta_sem_contato(self):
        msgs = [
            msg(1, datetime(2026, 10, 1, 9, 0), "cliente", "G", nome="Risco", lid="L1", papel="Stakeholder"),
            msg(2, datetime(2026, 10, 9, 9, 0), "equipe", "G", nome="Eq", lid="LE"),
            msg(3, datetime(2026, 10, 10, 9, 0), "cliente", "G", nome="OK", lid="L2", papel="Stakeholder"),
        ]
        risco = [c["nome"] for c in analise.clientes_em_risco(msgs, 3)]
        self.assertIn("Risco", risco)
        self.assertNotIn("OK", risco)


class TestTemposAutor(unittest.TestCase):
    def test_resposta_e_sem_resposta(self):
        base = datetime(2026, 10, 5, 9, 0)
        msgs = [
            msg(1, base, "cliente", "G", nome="C", lid="L1"),
            msg(2, base + timedelta(minutes=10), "equipe", "G", nome="E"),
            msg(3, base + timedelta(minutes=20), "cliente", "G", nome="C", lid="L1"),
        ]
        tempos, sem = analise._tempos_autor(msgs, "lid", "L1")
        self.assertEqual(tempos, [10.0])
        self.assertEqual(sem, 1)

    def test_msgs_sem_resposta(self):
        base = datetime(2026, 10, 5, 9, 0)
        sem = [
            msg(1, base, "cliente", "G", nome="C", lid="L1"),
            msg(2, base + timedelta(minutes=10), "cliente", "G", nome="C", lid="L1"),
        ]
        self.assertEqual(len(analise.msgs_sem_resposta(sem, "cliente", "equipe")), 2)
        com = [
            msg(1, base, "cliente", "G", nome="C", lid="L1"),
            msg(2, base + timedelta(minutes=5), "equipe", "G", nome="E"),
        ]
        self.assertEqual(len(analise.msgs_sem_resposta(com, "cliente", "equipe")), 0)


class TestGaps(unittest.TestCase):
    def test_gaps_resumo(self):
        turns = [
            {"tipo": "cliente", "start": datetime(2026, 10, 1, 9, 0), "end": datetime(2026, 10, 1, 9, 5), "n": 1},
            {"tipo": "equipe", "start": datetime(2026, 10, 1, 9, 15), "end": datetime(2026, 10, 1, 9, 16), "n": 1},
        ]
        g = analise.gaps(turns)
        self.assertEqual(g, [10.0])
        r = analise.gaps_resumo(g)
        self.assertEqual(r["media"], 10.0)
        self.assertEqual(r["max"], 10.0)


if __name__ == "__main__":
    unittest.main()
