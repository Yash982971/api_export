import os
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.graphics.shapes import Drawing, Rect, String, Circle

def build_presentation_pdf(output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 11 x 8.5 landscape
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Colors
    bg_color = colors.HexColor('#0B0E1B')
    card_bg = colors.HexColor('#161B30')
    card_border = colors.HexColor('#232B48')
    gold_accent = colors.HexColor('#D4AF37')
    light_gold = colors.HexColor('#E5C158')
    text_white = colors.HexColor('#FFFFFF')
    text_muted = colors.HexColor('#94A3B8')
    
    brand_header = ParagraphStyle('BH', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=gold_accent, spaceAfter=15)
    cover_title = ParagraphStyle('CT', fontName='Helvetica-Bold', fontSize=32, leading=38, textColor=text_white)
    cover_subtitle = ParagraphStyle('CST', fontName='Helvetica', fontSize=16, leading=22, textColor=light_gold, spaceAfter=8)
    body_muted = ParagraphStyle('BM', fontName='Helvetica', fontSize=11, leading=16, textColor=text_muted)
    sec_title = ParagraphStyle('ST', fontName='Helvetica-Bold', fontSize=24, leading=30, textColor=text_white, spaceAfter=15)
    card_hdr = ParagraphStyle('CH', fontName='Helvetica-Bold', fontSize=14, leading=18, textColor=text_white, spaceAfter=6)
    card_dsc = ParagraphStyle('CD', fontName='Helvetica', fontSize=10, leading=14, textColor=text_muted)
    sku_ttl = ParagraphStyle('SKUT', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=text_white, alignment=1)
    sku_code = ParagraphStyle('SKUC', fontName='Helvetica', fontSize=9, leading=12, textColor=gold_accent, alignment=1)
    
    story = []
    
    def draw_bg(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(bg_color)
        canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=True, stroke=False)
        if doc.page > 1:
            canvas.setFont("Helvetica-Bold", 8)
            canvas.setFillColor(colors.HexColor('#64748B'))
            canvas.drawString(36, 20, "PRODUCT ZONE INTERNATIONAL")
            canvas.drawRightString(doc.pagesize[0] - 36, 20, f"0{doc.page} / 09")
        canvas.restoreState()

    # PAGE 1: COVER
    story.append(Paragraph("P R O D U C T   Z O N E   I N T E R N A T I O N A L", brand_header))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Crystal Candle Holders<br/>&amp; Décor", cover_title))
    story.append(Spacer(1, 15))
    story.append(Paragraph("Premium Glass Candle Holder Collection — Export Range", cover_subtitle))
    story.append(Paragraph("Crafted for Global Markets | Wholesale &amp; Bulk Supply", body_muted))
    story.append(Spacer(1, 40))
    
    stat_data = [
        [
            Paragraph("<b>23+</b>", ParagraphStyle('St1', fontName='Helvetica-Bold', fontSize=28, leading=32, textColor=text_white)),
            Paragraph("<b>6</b>", ParagraphStyle('St2', fontName='Helvetica-Bold', fontSize=28, leading=32, textColor=text_white)),
            Paragraph("<b>100%</b>", ParagraphStyle('St3', fontName='Helvetica-Bold', fontSize=28, leading=32, textColor=text_white))
        ],
        [
            Paragraph("SKUs", body_muted),
            Paragraph("Design Collections", body_muted),
            Paragraph("Export-Ready", body_muted)
        ]
    ]
    t_stat = Table(stat_data, colWidths=[150, 180, 180])
    t_stat.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
    story.append(t_stat)
    story.append(PageBreak())

    # PAGE 2: INTRODUCTION
    story.append(Paragraph("I N T R O D U C T I O N", brand_header))
    story.append(Paragraph("Who We Are &amp; Why Partner With Us", sec_title))
    story.append(Paragraph(
        "Product Zone International is a manufacturer and exporter of decorative glass candle holders, supplying home décor wholesalers, importers and retail chains across global markets. Our Crystal Candle Holder range spans 23 SKUs across six design collections — from faceted crystal-cut votives to statement large-format pieces — engineered for consistent quality at bulk-order volumes.",
        body_muted
    ))
    story.append(Spacer(1, 25))
    
    c1 = [Paragraph("<b>23+ SKUs</b>", card_hdr), Paragraph("Faceted, ribbed, dimpled, hobnail, frosted &amp; metallic glass designs in one catalogue", card_dsc)]
    c2 = [Paragraph("<b>Bulk-Ready Production</b>", card_hdr), Paragraph("High-volume manufacturing capacity to fulfill large international orders on time", card_dsc)]
    c3 = [Paragraph("<b>Competitive FOB Pricing</b>", card_hdr), Paragraph("Factory-direct rates that protect your margins in any market", card_dsc)]
    c4 = [Paragraph("<b>Custom Finishes</b>", card_hdr), Paragraph("Gold, clear, frosted, dimpled &amp; faceted finishes — tailored to your buyer's market", card_dsc)]
    
    t_intro = Table([[c1, c2, c3, c4]], colWidths=[175, 175, 175, 175])
    t_intro.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), card_bg),
        ('BOX', (0,0), (-1,-1), 1, card_border),
        ('INNERGRID', (0,0), (-1,-1), 1, card_border),
        ('PADDING', (0,0), (-1,-1), 12),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_intro)
    story.append(PageBreak())

    # Helper for Collection Pages
    def build_collection(col_num, col_title, items, best_for):
        el = []
        el.append(Paragraph(f"C O L L E C T I O N   {col_num}   O F   6", brand_header))
        el.append(Paragraph(col_title, sec_title))
        el.append(Spacer(1, 10))
        
        c_width = 175 if len(items) == 4 else 235
        row_cells = []
        for name, sku in items:
            d = Drawing(c_width - 20, 110)
            d.add(Rect(0, 0, c_width - 20, 110, fillColor=colors.HexColor('#1E253B'), strokeColor=card_border, rx=6, ry=6))
            d.add(Circle((c_width - 20)/2, 55, 24, fillColor=colors.HexColor('#2A334F'), strokeColor=gold_accent))
            d.add(String((c_width - 20)/2, 51, "🕯️", fontName="Helvetica", fontSize=18, textAnchor="middle"))
            row_cells.append([d, Spacer(1, 6), Paragraph(name, sku_ttl), Paragraph(sku, sku_code)])
            
        t_col = Table([row_cells], colWidths=[c_width] * len(items))
        t_col.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), card_bg),
            ('BOX', (0,0), (-1,-1), 1, card_border),
            ('INNERGRID', (0,0), (-1,-1), 1, card_border),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER')
        ]))
        el.append(t_col)
        el.append(Spacer(1, 20))
        
        t_best = Table([[Paragraph(f"<i><b>Best for:</b> {best_for}</i>", ParagraphStyle('BF', fontName='Helvetica', fontSize=10, textColor=text_white))]], colWidths=[710])
        t_best.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#161C33')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#2A355A')),
            ('PADDING', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'LEFT')
        ]))
        el.append(t_best)
        el.append(PageBreak())
        return el

    # PAGES 3-8: 6 COLLECTIONS
    story.extend(build_collection(1, "Classic Ribbed & Fluted Clear Glass", [("Ribbed Clear Votive", "PZI-2917"), ("Tall Fluted Clear Cylinder", "PZI-2918"), ("Faceted Clear Cylinder", "PZI-2921"), ("Ribbed Tall Cylinder", "PZI-2923")], "Restaurants, event planners, hospitality décor, mass-market wholesale"))
    story.extend(build_collection(2, "Diamond & Faceted Cut Crystal", [("Diamond-Cut Clear Votive", "PZI-2920"), ("Faceted Crystal Tealight", "PZI-2926"), ("Diamond-Cut Cylinder", "PZI-2927"), ("Faceted Crystal Votive", "PZI-2932")], "Luxury retail, boutique gifting, wedding & event wholesale"))
    story.extend(build_collection(3, "Dimpled & Hobnail Textured Glass", [("Dimpled Clear Bowl", "PZI-2922"), ("Hobnail Clear Votive", "PZI-2924"), ("Hobnail Textured Votive", "PZI-2928"), ("Dimpled Round Votive", "PZI-2934")], "Home décor chains, spa & wellness, boho gifting, farmhouse retail"))
    story.extend(build_collection(4, "Wave & Organic Cut Bowls", [("Wave-Cut Frosted Bowl", "PZI-2919"), ("Organic-Cut Tall Cylinder", "PZI-2933"), ("Wave-Cut Clear Cylinder", "PZI-2935"), ("Organic-Cut Round Votive", "PZI-2936")], "Vintage retail, garden décor, seasonal & gifting collections"))
    story.extend(build_collection(5, "Gold Metallic & Statement Pieces", [("Dimpled Gold Metallic Votive", "PZI-2925"), ("Statement Clear Bowl", "PZI-2937"), ("Metallic Accent Votive", "PZI-2938"), ("Statement Cylinder", "PZI-2942")], "Middle Eastern markets, festive collections, hotel amenities"))
    story.extend(build_collection(6, "Large-Format & Specialty Collection", [("Large Statement Cylinder", "PZI-2944"), ("Wide Statement Bowl", "PZI-2945"), ("Frosted-Base Cylinder", "PZI-2946")], "Valentine's Day & Christmas wholesale, luxury retail, statement display pieces"))

    # PAGE 9: LET'S WORK TOGETHER
    story.append(Paragraph("L E T ' S   W O R K   T O G E T H E R", brand_header))
    story.append(Paragraph("Start Your Export Partnership Today", sec_title))
    story.append(Spacer(1, 10))
    
    fc1 = [Paragraph("<b>Request a Catalogue</b>", card_hdr), Paragraph("Full product specs, dimensions &amp; pricing on request", card_dsc)]
    fc2 = [Paragraph("<b>Sample Orders</b>", card_hdr), Paragraph("Sample sets available before committing to bulk quantities", card_dsc)]
    fc3 = [Paragraph("<b>MOQ Flexibility</b>", card_hdr), Paragraph("Minimum order quantities suited to importers of all sizes", card_dsc)]
    fc4 = [Paragraph("<b>Private Label</b>", card_hdr), Paragraph("Custom branding &amp; packaging for established buyers", card_dsc)]
    fc5 = [Paragraph("<b>Reliable Shipping</b>", card_hdr), Paragraph("Experienced in export documentation, freight &amp; compliance", card_dsc)]
    fc6 = [Paragraph("<b>Long-Term Partnership</b>", card_hdr), Paragraph("Dedicated account support for repeat export buyers", card_dsc)]
    
    t_cta = Table([[fc1, fc2, fc3], [fc4, fc5, fc6]], colWidths=[235, 235, 235])
    t_cta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), card_bg),
        ('BOX', (0,0), (-1,-1), 1, card_border),
        ('INNERGRID', (0,0), (-1,-1), 1, card_border),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_cta)
    story.append(Spacer(1, 15))
    
    cta_footer = Paragraph(
        "<i>Product Zone International — Illuminating Homes Across the World</i><br/>"
        "<b>Interested in becoming a wholesale or distribution partner? Contact us today for catalogue, pricing and samples.</b>",
        ParagraphStyle('CTAFooter', fontName='Helvetica', fontSize=10, leading=14, textColor=light_gold, alignment=1)
    )
    t_foot = Table([[cta_footer]], colWidths=[710])
    t_foot.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#13182B')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#2E395E')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    story.append(t_foot)

    doc.build(story, onFirstPage=draw_bg, onLaterPages=draw_bg)
    print(f"Presentation PDF compiled to {output_path}")

if __name__ == '__main__':
    target = os.path.join(os.path.dirname(__file__), 'assets', 'company_presentation.pdf')
    build_presentation_pdf(target)
