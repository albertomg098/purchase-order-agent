"""PDF fixture generator for evaluation scenarios.

Generates PDFs using reportlab that match the structure of purchase order documents.
Each PDF has a companion JSON file with ground truth extraction data.

Usage:
    python -m evals.generate_fixtures
"""
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


FIXTURES_DIR = Path("evals/fixtures")

FIXTURE_CONFIGS = [
    # ── Happy path — complete POs ──
    {
        "id": "complete_01",
        "category": "happy_path",
        "fields": {
            "order_id": "PO-2025-001",
            "customer": "Acme Logistics Ltd.",
            "pickup_location": "Warehouse A, 123 Industrial Rd, Madrid",
            "delivery_location": "Retail Hub B, 456 Market St, Barcelona",
            "delivery_datetime": "2025-01-18, 08:00",
            "driver_name": "Juan Pérez",
            "driver_phone": "+34 600 123 456",
        },
    },
    {
        "id": "complete_02",
        "category": "happy_path",
        "fields": {
            "order_id": "PO-2025-042",
            "customer": "Mediterranean Freight Co.",
            "pickup_location": "Port Terminal C, Dock 7, Valencia",
            "delivery_location": "Distribution Center, 89 Logistics Ave, Zaragoza",
            "delivery_datetime": "2025-02-20, 14:30",
            "driver_name": "María García López",
            "driver_phone": "+34 611 234 567",
        },
    },
    {
        "id": "complete_03",
        "category": "happy_path",
        "fields": {
            "order_id": "PO-2025-088",
            "customer": "TransIberia Express S.A.",
            "pickup_location": "Cold Storage Unit 5, Mercamadrid, Madrid",
            "delivery_location": "SuperFresh Market, 12 Paseo de Gracia, Barcelona",
            "delivery_datetime": "2025-03-10, 06:00",
            "driver_name": "Pedro Sánchez Ruiz",
            "driver_phone": "+34 622 987 654",
        },
    },
    {
        "id": "complete_04",
        "category": "happy_path",
        "fields": {
            "order_id": "PO-2025-103",
            "customer": "Iberian Cold Chain Ltd.",
            "pickup_location": "Freezer Warehouse 3, Pol. Ind. Norte, Vitoria",
            "delivery_location": "Hospital Central, Av. Sanidad 1, Pamplona",
            "delivery_datetime": "2025-04-05, 10:00",
            "driver_name": "Elena Fernández",
            "driver_phone": "+34 633 111 222",
        },
    },
    {
        "id": "complete_05",
        "category": "happy_path",
        "fields": {
            "order_id": "PO-2025-150",
            "customer": "SolTrans Logistics",
            "pickup_location": "Nave 12, Pol. Ind. Guadalhorce, Málaga",
            "delivery_location": "Centro Comercial Nervión, Sevilla",
            "delivery_datetime": "2025-05-22, 16:00",
            "driver_name": "Antonio Morales",
            "driver_phone": "+34 644 333 444",
        },
    },
    # ── Missing fields ──
    {
        "id": "missing_phone_01",
        "category": "missing_fields",
        "fields": {
            "order_id": "PO-2025-010",
            "customer": "NorthStar Shipping",
            "pickup_location": "Warehouse D, 10 Port Rd, Bilbao",
            "delivery_location": "Store E, 22 Gran Vía, Madrid",
            "delivery_datetime": "2025-03-01, 09:00",
            "driver_name": "Carlos Ruiz",
            "driver_phone": None,
        },
    },
    {
        "id": "missing_driver_01",
        "category": "missing_fields",
        "fields": {
            "order_id": "PO-2025-011",
            "customer": "Iberian Express",
            "pickup_location": "Factory F, Industrial Park, Sevilla",
            "delivery_location": "Warehouse G, 5 Commerce St, Málaga",
            "delivery_datetime": "2025-03-05, 11:00",
            "driver_name": None,
            "driver_phone": None,
        },
    },
    {
        "id": "missing_delivery_date_01",
        "category": "missing_fields",
        "fields": {
            "order_id": "PO-2025-012",
            "customer": "Costa Logistics",
            "pickup_location": "Terminal H, 33 Harbor Blvd, Alicante",
            "delivery_location": "Depot I, 77 Industrial Rd, Murcia",
            "delivery_datetime": None,
            "driver_name": "Ana Martín",
            "driver_phone": "+34 622 345 678",
        },
    },
    {
        "id": "missing_pickup_01",
        "category": "missing_fields",
        "fields": {
            "order_id": "PO-2025-013",
            "customer": "RápidoTrans S.L.",
            "pickup_location": None,
            "delivery_location": "Almacén Central, C/ Logística 8, Toledo",
            "delivery_datetime": "2025-04-12, 07:30",
            "driver_name": "Luis Herrera",
            "driver_phone": "+34 655 777 888",
        },
    },
    {
        "id": "missing_customer_01",
        "category": "missing_fields",
        "fields": {
            "order_id": "PO-2025-014",
            "customer": None,
            "pickup_location": "Puerto Seco, Coslada, Madrid",
            "delivery_location": "Plataforma Logística, Zaragoza",
            "delivery_datetime": "2025-05-01, 13:00",
            "driver_name": "Sofía Navarro",
            "driver_phone": "+34 666 999 000",
        },
    },
    # ── Malformed PDFs ──
    {
        "id": "malformed_01",
        "category": "malformed_pdf",
        "fields": {
            "order_id": "PO2025-020",
            "customer": "GLOBAL TRANS S.L.",
            "pickup_location": "C/ Industria 45, Pol. Ind. Sur, Granada",
            "delivery_location": "Avda. Constitución 12, 3ºA, Córdoba",
            "delivery_datetime": "18 enero 2025 a las 8h",
            "driver_name": "josé antonio lópez",
            "driver_phone": "600.123.456",
        },
        "layout": "scrambled",
    },
    {
        "id": "malformed_02",
        "category": "malformed_pdf",
        "fields": {
            "order_id": "PO 2025/021",
            "customer": "transportes garcia & hijos",
            "pickup_location": "NAVE 7 POL IND LAS QUEMADAS CORDOBA",
            "delivery_location": "c/ real 45 bajo jaen",
            "delivery_datetime": "20/02/2025 - 15h",
            "driver_name": "MIGUEL ÁNGEL TORRES",
            "driver_phone": "34 677-888-999",
        },
        "layout": "scrambled",
    },
    {
        "id": "malformed_03",
        "category": "malformed_pdf",
        "fields": {
            "order_id": "P.O.-2025-022",
            "customer": "Lgtcs. Mediterráneo",
            "pickup_location": "Muelle 3, Puerto de Cartagena, Murcia",
            "delivery_location": "Pza. Mayor s/n, Albacete (detrás del ayuntamiento)",
            "delivery_datetime": "2025.03.15 09:00AM",
            "driver_name": "Fco. Javier Ruiz Mtnz.",
            "driver_phone": "(+34) 688 12 34 56",
        },
        "layout": "scrambled",
    },
    {
        "id": "malformed_04",
        "category": "malformed_pdf",
        "fields": {
            "order_id": "2025-PO-023",
            "customer": "EAST-WEST CARGO SLU",
            "pickup_location": "Apt. Correos 234 - Zona Franca Barcelona",
            "delivery_location": "KM 34 Autovía A-2, Lleida",
            "delivery_datetime": "Abr 10, 2025 @ 11AM",
            "driver_name": "R. Fernández",
            "driver_phone": "+34600111222",
        },
        "layout": "scrambled",
    },
    {
        "id": "malformed_05",
        "category": "malformed_pdf",
        "fields": {
            "order_id": "po-2025-024",
            "customer": "HERMANOS LÓPEZ TRANSPORT",
            "pickup_location": "Ctra. Nacional 340 km 12, Algeciras",
            "delivery_location": "Mercasevilla, Módulo 5, Sevilla",
            "delivery_datetime": "mayo 2025, dia 5, 7 de la mañana",
            "driver_name": "LÓPEZ GARCÍA, Manuel",
            "driver_phone": "0034 699 00 11 22",
        },
        "layout": "scrambled",
    },
    # ── Not a PO ──
    {
        "id": "not_po_newsletter_01",
        "category": "not_a_po",
        "doc_type": "newsletter",
        "title": "Monthly Logistics Newsletter",
        "body_text": (
            "Welcome to the March 2025 edition of our logistics newsletter.\n\n"
            "Industry trends: Supply chain disruptions continue to affect Mediterranean routes.\n"
            "New regulations for cold chain transport take effect April 1st.\n\n"
            "Best regards,\nThe Logistics Team"
        ),
    },
    {
        "id": "not_po_invoice_01",
        "category": "not_a_po",
        "doc_type": "invoice",
        "title": "Invoice #INV-2025-5001",
        "body_text": (
            "Bill To: Traza Logistics S.L.\n"
            "Amount Due: €4,500.00\n"
            "Due Date: March 15, 2025\n\n"
            "Services rendered: Fleet maintenance Q1 2025\n"
            "Payment terms: Net 30"
        ),
    },
    {
        "id": "not_po_inquiry_01",
        "category": "not_a_po",
        "doc_type": "inquiry",
        "title": "Service Inquiry",
        "body_text": (
            "Dear Traza Team,\n\n"
            "We are interested in your logistics services for our upcoming product launch.\n"
            "Could you send us a quote for 50 deliveries per month in the Madrid area?\n\n"
            "Thank you,\nJavier from StartupCo"
        ),
    },
    {
        "id": "not_po_spam_01",
        "category": "not_a_po",
        "doc_type": "spam",
        "title": "URGENT: Claim Your Prize!",
        "body_text": (
            "Congratulations! You have been selected as the winner of our annual draw.\n"
            "Click here to claim your €10,000 prize immediately.\n"
            "This offer expires in 24 hours. Act now!\n\n"
            "Terms and conditions apply."
        ),
    },
    {
        "id": "not_po_internal_01",
        "category": "not_a_po",
        "doc_type": "internal_memo",
        "title": "Internal Memo: Office Closure",
        "body_text": (
            "To all staff,\n\n"
            "Please note that the office will be closed on Friday, March 28th\n"
            "for the annual company retreat.\n\n"
            "Normal operations resume Monday, March 31st.\n\n"
            "HR Department"
        ),
    },
    # ── Ambiguous ──
    {
        "id": "ambiguous_truncated_phone_01",
        "category": "ambiguous",
        "fields": {
            "order_id": "PO-2025-030",
            "customer": "Atlas Cargo S.L.",
            "pickup_location": "Nave 2, Pol. Ind. Henares, Guadalajara",
            "delivery_location": "C/ Comercio 15, Valladolid",
            "delivery_datetime": "2025-06-01, 10:00",
            "driver_name": "Roberto Díaz",
            "driver_phone": "+34 6...",
        },
    },
    {
        "id": "ambiguous_abbreviated_addr_01",
        "category": "ambiguous",
        "fields": {
            "order_id": "PO-2025-031",
            "customer": "Quick Del. Services",
            "pickup_location": "Pol. Ind. S. Fernando, Cádiz",
            "delivery_location": "Av. Constitución, Huelva (preg. por José)",
            "delivery_datetime": "2025-06-15, 08:00",
            "driver_name": "J. Martínez",
            "driver_phone": "+34 655 432 100",
        },
    },
    {
        "id": "ambiguous_no_year_01",
        "category": "ambiguous",
        "fields": {
            "order_id": "PO-2025-032",
            "customer": "EuroTrans Continental",
            "pickup_location": "Terminal de Carga, Aeropuerto de Barajas, Madrid",
            "delivery_location": "Centro Logístico, Pol. Ind. Júndiz, Vitoria",
            "delivery_datetime": "15 de marzo, 14:00",
            "driver_name": "Iñaki Zubiaurre",
            "driver_phone": "+34 688 765 432",
        },
    },
    {
        "id": "ambiguous_similar_addresses_01",
        "category": "ambiguous",
        "fields": {
            "order_id": "PO-2025-033",
            "customer": "Doble Vía Logistics",
            "pickup_location": "C/ Industria 10, Pol. Ind. Norte, Getafe, Madrid",
            "delivery_location": "C/ Industria 10, Pol. Ind. Sur, Leganés, Madrid",
            "delivery_datetime": "2025-07-01, 09:00",
            "driver_name": "Carmen Delgado Ruiz",
            "driver_phone": "+34 611 222 333",
        },
    },
    {
        "id": "ambiguous_mixed_lang_01",
        "category": "ambiguous",
        "fields": {
            "order_id": "PO-2025-034",
            "customer": "Cross-Border Freight EU",
            "pickup_location": "Entrepôt 4, Zone Industrielle, Perpignan, France",
            "delivery_location": "Almacén B7, Pol. Logístic, La Jonquera, Girona",
            "delivery_datetime": "2025-07-20, 11:30",
            "driver_name": "Jean-Pierre / Juan Pedro Martín",
            "driver_phone": "+33 6 12 34 56 78 / +34 612 345 678",
        },
    },
]


FIELD_LABELS = {
    "order_id": "Order ID",
    "customer": "Customer",
    "pickup_location": "Pickup Location",
    "delivery_location": "Delivery Location",
    "delivery_datetime": "Delivery Date & Time",
    "driver_name": "Truck Driver",
    "driver_phone": "Driver Phone",
}


def build_standard_pdf(path: Path, fields: dict) -> None:
    """Generate a standard PO PDF with a table-like layout."""
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle("POTitle", parent=styles["Title"], fontSize=20, spaceAfter=20)
    elements.append(Paragraph("Purchase Order", title_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Fields table
    table_data = []
    for key, label in FIELD_LABELS.items():
        value = fields.get(key)
        display = value if value is not None else ""
        table_data.append([label, display])

    table = Table(table_data, colWidths=[5 * cm, 12 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8e8e8")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 1 * cm))

    # Footer
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    elements.append(Paragraph(
        "Please handle with care. Ensure delivery is completed within the specified timeframe. "
        "Contact the driver directly for any scheduling changes.",
        footer_style,
    ))

    doc.build(elements)


def build_scrambled_pdf(path: Path, fields: dict) -> None:
    """Generate a malformed PO PDF with non-standard layout."""
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    elements = []

    # Messy title
    title_style = ParagraphStyle("MessyTitle", parent=styles["Title"], fontSize=16, spaceAfter=10)
    elements.append(Paragraph("PURCHASE ORDER // ORDEN DE COMPRA", title_style))
    elements.append(Spacer(1, 0.3 * cm))

    # Dump fields as plain text paragraphs (no table structure)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=11, leading=16)
    field_order = list(fields.keys())
    # Shuffle-ish: put some fields in odd order
    reordered = [field_order[2], field_order[0], field_order[5], field_order[1],
                 field_order[4], field_order[3], field_order[6]]

    for key in reordered:
        value = fields.get(key)
        if value is not None:
            label = FIELD_LABELS.get(key, key)
            elements.append(Paragraph(f"<b>{label}:</b> {value}", body_style))
            elements.append(Spacer(1, 0.2 * cm))

    elements.append(Spacer(1, 0.5 * cm))
    note_style = ParagraphStyle("Note", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    elements.append(Paragraph("--- Documento generado automáticamente / Auto-generated document ---", note_style))

    doc.build(elements)


def build_non_po_pdf(path: Path, title: str, body_text: str) -> None:
    """Generate a non-PO PDF (invoice, newsletter, etc.)."""
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle("DocTitle", parent=styles["Title"], fontSize=18, spaceAfter=20)
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.5 * cm))

    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=11, leading=16)
    for line in body_text.split("\n"):
        if line.strip():
            elements.append(Paragraph(line, body_style))
        else:
            elements.append(Spacer(1, 0.3 * cm))

    doc.build(elements)


def build_ground_truth(config: dict) -> dict | None:
    """Build the ground truth JSON for a fixture config. Returns None for non-PO docs."""
    if "fields" not in config:
        return None

    fields = config["fields"]
    return {
        "order_id": fields.get("order_id"),
        "customer": fields.get("customer"),
        "pickup_location": fields.get("pickup_location"),
        "delivery_location": fields.get("delivery_location"),
        "delivery_datetime": fields.get("delivery_datetime"),
        "driver_name": fields.get("driver_name"),
        "driver_phone": fields.get("driver_phone"),
    }


def generate_all():
    """Generate all PDF fixtures and companion JSON files."""
    count = 0
    for config in FIXTURE_CONFIGS:
        category = config["category"]
        fixture_id = config["id"]

        category_dir = FIXTURES_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = category_dir / f"{fixture_id}.pdf"

        if config["category"] == "not_a_po":
            build_non_po_pdf(pdf_path, config["title"], config["body_text"])
        elif config.get("layout") == "scrambled":
            build_scrambled_pdf(pdf_path, config["fields"])
        else:
            build_standard_pdf(pdf_path, config["fields"])

        # Ground truth JSON
        ground_truth = build_ground_truth(config)
        if ground_truth is not None:
            json_path = category_dir / f"{fixture_id}.json"
            with open(json_path, "w") as f:
                json.dump(ground_truth, f, indent=2, ensure_ascii=False)

        count += 1
        print(f"  Generated: {category}/{fixture_id}.pdf")

    print(f"\nTotal: {count} fixtures generated in {FIXTURES_DIR}")


if __name__ == "__main__":
    generate_all()
