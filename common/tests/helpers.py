from decimal import Decimal

from django.contrib.auth import get_user_model

from bidders.models import Bidder, BidderMember
from documents.models import Document
from procurement.models import ContractProcess


def create_user(username="tester"):
    User = get_user_model()
    return User.objects.create_user(username=username, password="test12345")


def create_process(code="PROC-001", name="Proceso 1"):
    return ContractProcess.objects.create(
        code=code,
        name=name,
        entity_name="Entidad Demo",
        process_type="licitacion_publica",
        modality="pliego_tipo",
    )


def create_bidder(process, identification_number="900000001", bidder_type="individual", name="Proponente 1"):
    return Bidder.objects.create(
        process=process,
        name=name,
        identification_type="NIT",
        identification_number=identification_number,
        bidder_type=bidder_type,
    )


def create_bidder_member(bidder, identification_number="100000001", name="Integrante 1", percentage=Decimal("50")):
    return BidderMember.objects.create(
        bidder=bidder,
        name=name,
        identification_type="CC",
        identification_number=identification_number,
        participation_percentage=percentage,
    )


def create_document(process, bidder=None, name="Documento 1", document_type="general"):
    return Document.objects.create(
        process=process,
        bidder=bidder,
        name=name,
        document_type=document_type,
    )
