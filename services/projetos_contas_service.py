"""Serviço de contas de mídia por projeto.

Responsável por validação/normalização, CRUD, troca de principal, desativação
e espelho dos campos legados (meta_account_id/google_account_id) usados por
Operação/Kanban enquanto a migração definitiva desses consumidores não ocorre.
"""
from typing import Any, Dict, List, Optional
import re

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from models import Projeto, ProjetoConta

PLATAFORMAS = {
    "meta_ads": "Meta Ads",
    "facebook_page": "Facebook Page",
    "instagram": "Instagram",
    "google_ads": "Google Ads",
    "ga4": "GA4",
}

_PREFIXOS = ("act_", "customers/", "properties/", "accounts/")

_ERROS_CONSTRAINT = {
    "uq_projetos_contas": "Essa conta já está cadastrada nesse projeto.",
    "uq_projetos_contas_principal": "Já existe uma conta principal nessa plataforma.",
    "ck_projetos_contas_conta_id_digitos": "O ID deve ter só números.",
    "ck_projetos_contas_plataforma": "Plataforma inválida.",
    "ck_projetos_contas_principal_ativo": "Uma conta inativa não pode ser principal.",
    "fk_projetos_contas_projeto": "Projeto não encontrado.",
}


def normalizar_conta_id(valor: Any) -> str:
    texto = str(valor or "").strip()
    baixo = texto.lower()
    for prefixo in _PREFIXOS:
        if baixo.startswith(prefixo):
            texto = texto[len(prefixo):]
            break
    texto = re.sub(r"[\s\-\.]", "", texto)
    if not texto.isdigit():
        raise ValueError("O ID deve ter só números.")
    if len(texto) > 100:
        raise ValueError("O ID da conta é muito longo.")
    return texto


def _bool(valor: Any, padrao: bool) -> bool:
    if isinstance(valor, bool):
        return valor
    if valor is None:
        return padrao
    if isinstance(valor, (int, float)):
        return bool(valor)
    texto = str(valor).strip().lower()
    if texto in ("1", "true", "sim", "on", "yes"):
        return True
    if texto in ("0", "false", "nao", "não", "off", "no", ""):
        return False
    return padrao


def _mensagem_erro(erro: IntegrityError) -> str:
    origem = getattr(erro, "orig", None)
    nome = getattr(getattr(origem, "diag", None), "constraint_name", None)
    if not nome:
        texto = str(origem or erro)
        for chave in _ERROS_CONSTRAINT:
            if chave in texto:
                nome = chave
                break
    return _ERROS_CONSTRAINT.get(nome or "", "Não foi possível salvar a conta.")


def _projeto(db, pipefy_id: int) -> Projeto:
    projeto = db.query(Projeto).filter_by(pipefy_id=pipefy_id).first()
    if not projeto:
        raise ValueError("Projeto não encontrado.")
    return projeto


def _conta(db, pipefy_id: int, conta_id: int) -> ProjetoConta:
    conta = db.query(ProjetoConta).filter_by(
        id=conta_id, projeto_pipefy_id=pipefy_id
    ).first()
    if not conta:
        raise ValueError("Conta não encontrada.")
    return conta


def _serializar(conta: ProjetoConta) -> Dict[str, Any]:
    return conta.to_dict()


def _validar_payload(data: Dict[str, Any], parcial: bool = False) -> Dict[str, Any]:
    data = data or {}
    saida: Dict[str, Any] = {}

    if "plataforma" in data or not parcial:
        plataforma = str(data.get("plataforma") or "").strip()
        if plataforma not in PLATAFORMAS:
            raise ValueError("Selecione uma plataforma válida.")
        saida["plataforma"] = plataforma

    if "conta_id" in data or not parcial:
        saida["conta_id"] = normalizar_conta_id(data.get("conta_id"))

    if "frente" in data or not parcial:
        frente = str(data.get("frente") or "").strip()
        if len(frente) > 100:
            raise ValueError("A frente deve ter no máximo 100 caracteres.")
        saida["frente"] = frente or None

    if "descricao" in data or not parcial:
        descricao = str(data.get("descricao") or "").strip()
        saida["descricao"] = descricao or None

    if "principal" in data or not parcial:
        saida["principal"] = _bool(data.get("principal"), False)

    if "ativo" in data or not parcial:
        saida["ativo"] = _bool(data.get("ativo"), True)

    if saida.get("principal") and saida.get("ativo") is False:
        raise ValueError("Uma conta inativa não pode ser principal.")

    return saida


def listar(db, pipefy_id: int, incluir_inativas: bool = False) -> List[Dict[str, Any]]:
    _projeto(db, pipefy_id)
    query = db.query(ProjetoConta).filter_by(projeto_pipefy_id=pipefy_id)
    if not incluir_inativas:
        query = query.filter_by(ativo=True)
    contas = query.order_by(
        ProjetoConta.plataforma.asc(),
        ProjetoConta.principal.desc(),
        ProjetoConta.frente.asc(),
        ProjetoConta.id.asc(),
    ).all()
    return [_serializar(c) for c in contas]


def _desmarcar_principal(db, pipefy_id: int, plataforma: str, exceto_id: Optional[int], usuario: str) -> None:
    query = db.query(ProjetoConta).filter(
        ProjetoConta.projeto_pipefy_id == pipefy_id,
        ProjetoConta.plataforma == plataforma,
        ProjetoConta.principal.is_(True),
    )
    if exceto_id is not None:
        query = query.filter(ProjetoConta.id != exceto_id)
    query.update(
        {ProjetoConta.principal: False, ProjetoConta.updated_by: usuario},
        synchronize_session=False,
    )


def _espelhar_legado(db, projeto: Projeto) -> None:
    colunas = {"meta_ads": "meta_account_id", "google_ads": "google_account_id"}
    for plataforma, coluna in colunas.items():
        conta = (
            db.query(ProjetoConta)
            .filter_by(
                projeto_pipefy_id=projeto.pipefy_id,
                plataforma=plataforma,
                ativo=True,
            )
            .order_by(ProjetoConta.principal.desc(), ProjetoConta.id.asc())
            .first()
        )
        setattr(projeto, coluna, conta.conta_id if conta else None)


def criar(db, pipefy_id: int, data: Dict[str, Any], usuario: str) -> Dict[str, Any]:
    projeto = _projeto(db, pipefy_id)
    campos = _validar_payload(data, parcial=False)

    try:
        if campos["principal"]:
            _desmarcar_principal(db, pipefy_id, campos["plataforma"], None, usuario)
            db.flush()
        conta = ProjetoConta(
            projeto_pipefy_id=pipefy_id,
            plataforma=campos["plataforma"],
            conta_id=campos["conta_id"],
            frente=campos["frente"],
            descricao=campos["descricao"],
            principal=campos["principal"],
            ativo=campos["ativo"],
            updated_by=usuario,
        )
        db.add(conta)
        db.flush()
        _espelhar_legado(db, projeto)
        db.commit()
        db.refresh(conta)
        return _serializar(conta)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(_mensagem_erro(e)) from e


def atualizar(db, pipefy_id: int, conta_id: int, data: Dict[str, Any], usuario: str) -> Dict[str, Any]:
    projeto = _projeto(db, pipefy_id)
    conta = _conta(db, pipefy_id, conta_id)
    campos = _validar_payload(data, parcial=True)

    if "ativo" in campos and not campos["ativo"]:
        campos["principal"] = False
    if campos.get("principal") and not campos.get("ativo", conta.ativo):
        raise ValueError("Uma conta inativa não pode ser principal.")

    try:
        if campos.get("principal"):
            _desmarcar_principal(db, pipefy_id, campos.get("plataforma", conta.plataforma), conta.id, usuario)
            db.flush()
        for campo in ("plataforma", "conta_id", "frente", "descricao", "principal", "ativo"):
            if campo in campos:
                setattr(conta, campo, campos[campo])
        conta.updated_by = usuario
        db.flush()
        _espelhar_legado(db, projeto)
        db.commit()
        db.refresh(conta)
        return _serializar(conta)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(_mensagem_erro(e)) from e


def definir_principal(db, pipefy_id: int, conta_id: int, principal: bool, usuario: str) -> Dict[str, Any]:
    projeto = _projeto(db, pipefy_id)
    conta = _conta(db, pipefy_id, conta_id)
    principal = _bool(principal, True)

    if principal and not conta.ativo:
        raise ValueError("Uma conta inativa não pode ser principal.")

    try:
        if principal:
            _desmarcar_principal(db, pipefy_id, conta.plataforma, conta.id, usuario)
            db.flush()
        conta.principal = principal
        conta.updated_by = usuario
        db.flush()
        _espelhar_legado(db, projeto)
        db.commit()
        db.refresh(conta)
        return _serializar(conta)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(_mensagem_erro(e)) from e


def _frente_norm(valor: Any) -> str:
    return str(valor or "").strip()


def _texto(valor: Any) -> Optional[str]:
    if valor is None:
        return None
    if isinstance(valor, (list, tuple)):
        texto = ", ".join(str(v) for v in valor if v not in (None, ""))
    else:
        texto = str(valor)
    texto = texto.strip()
    return texto or None


def _conta_id_valor(valor: Any) -> Optional[str]:
    if valor is None:
        return None
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return normalizar_conta_id(valor)


def _buscar_slot(db, projeto: Projeto, plataforma: str, frente: str) -> Optional[ProjetoConta]:
    base = db.query(ProjetoConta).filter_by(
        projeto_pipefy_id=projeto.pipefy_id,
        plataforma=plataforma,
    )
    frente = _frente_norm(frente)
    if frente:
        return (
            base.filter(func.coalesce(func.btrim(ProjetoConta.frente), "") == frente)
            .order_by(ProjetoConta.principal.desc(), ProjetoConta.ativo.desc(), ProjetoConta.id.asc())
            .first()
        )

    # Slot sem frente: tenta a conta sem frente; se não houver, usa a padrão/primeira.
    row = (
        base.filter(func.coalesce(func.btrim(ProjetoConta.frente), "") == "")
        .order_by(ProjetoConta.principal.desc(), ProjetoConta.ativo.desc(), ProjetoConta.id.asc())
        .first()
    )
    if row:
        return row
    return (
        base.order_by(ProjetoConta.principal.desc(), ProjetoConta.ativo.desc(), ProjetoConta.id.asc())
        .first()
    )


def aplicar_mapeamentos_kanban(db, projeto: Projeto,
                               mapeamentos: List[Dict[str, Any]],
                               usuario: Optional[str] = None) -> None:
    """Upsert transacional das contas mapeadas por campos do Kanban.

    Cada mapeamento: {plataforma, frente, coluna, valor}.
    Não commita; o fluxo do card faz o commit.
    """
    agrupados: Dict[tuple, Dict[str, Any]] = {}
    for item in (mapeamentos or []):
        plataforma = str(item.get("plataforma") or "").strip()
        if plataforma not in PLATAFORMAS:
            raise ValueError("Plataforma inválida no mapeamento do Kanban.")
        coluna = item.get("coluna")
        if coluna not in ("conta_id", "descricao"):
            continue
        frente = _frente_norm(item.get("frente"))
        chave = (plataforma, frente)
        agrupados.setdefault(chave, {})[coluna] = item.get("valor")

    usuario = (usuario or "kanban")[:100]

    try:
        for (plataforma, frente), valores in agrupados.items():
            tem_conta_id = "conta_id" in valores
            conta_id = _conta_id_valor(valores.get("conta_id")) if tem_conta_id else None

            # Se o card já traz um conta_id existente, prioriza essa linha
            # (evita sobrescrever a principal quando o valor legado é de outra conta).
            conta = None
            if conta_id:
                conta = db.query(ProjetoConta).filter_by(
                    projeto_pipefy_id=projeto.pipefy_id,
                    plataforma=plataforma,
                    conta_id=conta_id,
                ).first()
            if conta is None:
                conta = _buscar_slot(db, projeto, plataforma, frente)

            if conta is None:
                if not conta_id:
                    print(f"[kanban→contas] slot {plataforma}/{frente or 'padrão'} sem conta_id; ignorado.")
                    continue
                conta = ProjetoConta(
                    projeto_pipefy_id=projeto.pipefy_id,
                    plataforma=plataforma,
                    conta_id=conta_id,
                    frente=frente or None,
                    descricao=_texto(valores.get("descricao")),
                    principal=False,
                    ativo=True,
                    updated_by=usuario,
                )
                db.add(conta)
                db.flush()
            else:
                if tem_conta_id:
                    if not conta_id:
                        continue
                    conta.conta_id = conta_id
                if "descricao" in valores:
                    conta.descricao = _texto(valores.get("descricao"))
                conta.updated_by = usuario
                db.flush()

        _espelhar_legado(db, projeto)
        db.flush()
    except IntegrityError as e:
        raise ValueError(_mensagem_erro(e)) from e


def definir_ativo(db, pipefy_id: int, conta_id: int, ativo: bool, usuario: str) -> Dict[str, Any]:
    projeto = _projeto(db, pipefy_id)
    conta = _conta(db, pipefy_id, conta_id)
    ativo = _bool(ativo, True)

    try:
        conta.ativo = ativo
        if not ativo:
            conta.principal = False
        conta.updated_by = usuario
        db.flush()
        _espelhar_legado(db, projeto)
        db.commit()
        db.refresh(conta)
        return _serializar(conta)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(_mensagem_erro(e)) from e
