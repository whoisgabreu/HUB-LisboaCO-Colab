import json

from flask import flash, redirect, render_template, request, url_for

from .. import bp, db, member_photos, view_utils
from ..config import get_config, reset_config, save_config, validar_config


def _membros_para_template():
    membros = []
    for registro in db.listar_membros():
        membro = dict(registro)
        membro["foto_tech_url"] = member_photos.foto_url(membro.get("email"))
        membros.append(membro)
    return membros


@bp.route("/configuracoes", methods=["GET", "POST"])
def configuracoes():
    if request.method == "POST":
        bruto = request.form.get("config_json", "")
        try:
            dados = json.loads(bruto)
        except json.JSONDecodeError as erro:
            flash(f"JSON inválido: {erro}", "erro")
        else:
            erros = validar_config(dados)
            if erros:
                for mensagem in erros:
                    flash(mensagem, "erro")
            else:
                save_config(dados)
                flash("Configurações salvas.", "ok")
                return redirect(url_for("painel_tech.configuracoes"))
        return render_template(
            "painel_tech/configuracoes.html",
            config=get_config(),
            config_json=bruto,
            membros=_membros_para_template(),
            usuarios_tech=db.listar_usuarios_tech(),
        )
    return render_template(
        "painel_tech/configuracoes.html",
        config=get_config(),
        config_json=json.dumps(get_config(), ensure_ascii=False, indent=2),
        membros=_membros_para_template(),
        usuarios_tech=db.listar_usuarios_tech(),
    )


@bp.route("/configuracoes/numeros", methods=["POST"])
def configuracoes_numeros():
    config = get_config()
    try:
        pesos = {
            chave: float(
                request.form.get(
                    f"peso_{chave}", config["prioridade"]["pesos"].get(chave, 0)
                )
            )
            for chave in ("impacto", "urgencia", "risco", "esforco")
        }
        bandas = {
            chave: float(
                request.form.get(
                    f"banda_{chave}", config["prioridade"]["bandas"].get(chave, 0)
                )
            )
            for chave in ("critica", "alta", "media")
        }
        dias_bloqueio = int(
            request.form.get("dias_bloqueio", config["saude"]["dias_bloqueio_alerta"])
        )
        dias_movimento = int(
            request.form.get("dias_movimento", config["saude"]["dias_sem_movimento"])
        )
        limite_ativo = int(
            request.form.get(
                "limite_ativo",
                config["capacidade"]["limite_ativo_padrao"],
            )
        )
        agenda = config.get("agenda", {})
        expediente = agenda.get("expediente", {})
        almoco = agenda.get("almoco", {})
        horas_esforco = agenda.get("horas_por_esforco", {})
        agenda_slot = int(request.form.get("agenda_slot", agenda.get("slot_min", 30)))
        expediente_inicio = request.form.get(
            "agenda_expediente_inicio", expediente.get("inicio", "09:00")
        )
        expediente_fim = request.form.get(
            "agenda_expediente_fim", expediente.get("fim", "18:00")
        )
        almoco_inicio = request.form.get(
            "agenda_almoco_inicio", almoco.get("inicio", "12:00")
        )
        almoco_fim = request.form.get(
            "agenda_almoco_fim", almoco.get("fim", "13:00")
        )
        agenda_horas = {
            chave: float(
                request.form.get(
                    f"agenda_horas_{chave}", horas_esforco.get(chave, 0)
                )
            )
            for chave in ("pequeno", "medio", "grande", "muito_grande")
        }
    except (TypeError, ValueError):
        flash("Valores numéricos inválidos.", "erro")
        return redirect(url_for("painel_tech.configuracoes"))

    config["prioridade"]["pesos"] = pesos
    config["prioridade"]["bandas"] = bandas
    config["saude"]["dias_bloqueio_alerta"] = max(0, dias_bloqueio)
    config["saude"]["dias_sem_movimento"] = max(0, dias_movimento)
    config["capacidade"]["limite_ativo_padrao"] = max(0, limite_ativo)

    agenda_config = config.setdefault("agenda", {})
    dias_selecionados = [
        chave
        for chave in ("seg", "ter", "qua", "qui", "sex")
        if chave in request.form.getlist("agenda_dia")
    ]
    if dias_selecionados:
        agenda_config["dias"] = dias_selecionados
    agenda_config["slot_min"] = max(1, agenda_slot)
    agenda_config["expediente"] = {
        "inicio": expediente_inicio,
        "fim": expediente_fim,
    }
    agenda_config["almoco"] = {"inicio": almoco_inicio, "fim": almoco_fim}
    agenda_config["horas_por_esforco"] = agenda_horas

    erros = validar_config(config)
    if erros:
        for mensagem in erros:
            flash(mensagem, "erro")
    else:
        save_config(config)
        flash("Pesos e limiares salvos.", "ok")
    return redirect(url_for("painel_tech.configuracoes"))


@bp.route("/configuracoes/reset", methods=["POST"])
def configuracoes_reset():
    reset_config()
    flash("Configurações restauradas para o padrão.", "ok")
    return redirect(url_for("painel_tech.configuracoes"))


def _resposta_membros(mensagem, tipo="ok"):
    if view_utils.quer_fragmento():
        view_utils.enfileirar_toast(mensagem, tipo)
        return view_utils.anexar_toasts(
            render_template(
                "painel_tech/partials/_membros.html",
                membros=_membros_para_template(),
                usuarios_tech=db.listar_usuarios_tech(),
            )
        )
    flash(mensagem, tipo)
    return redirect(request.referrer or url_for("painel_tech.configuracoes"))


@bp.route("/membros", methods=["POST"])
def membro_criar():
    email = (request.form.get("email") or "").strip().lower()
    tech = db.listar_usuarios_tech()
    escolhido = next((u for u in tech if (u.get("email") or "").lower() == email), None)
    if not escolhido:
        return _resposta_membros(
            "Selecione um usuário com a posição TECH para ser membro do painel.", "erro"
        )
    db.criar_membro(escolhido["nome"], escolhido.get("email"), escolhido.get("id"))
    return _resposta_membros(f"{escolhido['nome']} adicionado como membro.", "ok")


@bp.route("/membros/<int:membro_id>/foto", methods=["POST"])
def membro_foto(membro_id):
    membro = next(
        (item for item in db.listar_membros() if item.get("id") == membro_id),
        None,
    )
    if not membro:
        return _resposta_membros("Membro não encontrado.", "erro")

    try:
        member_photos.salvar_foto(membro.get("email"), request.files.get("foto"))
    except member_photos.FotoMembroInvalida as erro:
        return _resposta_membros(str(erro), "erro")

    return _resposta_membros(f"Foto de {membro['nome']} atualizada.", "ok")


@bp.route("/membros/<int:membro_id>/capacidade", methods=["POST"])
def membro_capacidade(membro_id):
    bruto = (request.form.get("capacidade") or "").strip()
    try:
        capacidade = int(bruto) if bruto else None
        if capacidade is not None and capacidade < 0:
            raise ValueError
    except ValueError:
        return _resposta_membros(
            "Capacidade deve ser um número maior ou igual a 0 (ou vazio).", "erro"
        )
    db.atualizar_membro_capacidade(membro_id, capacidade)
    return _resposta_membros("Capacidade do membro atualizada.", "ok")


@bp.route("/membros/<int:membro_id>/excluir", methods=["POST"])
def membro_excluir(membro_id):
    db.excluir_membro(membro_id)
    return _resposta_membros("Membro removido.", "ok")
