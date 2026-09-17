import os
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.graphics.shapes import Drawing, Rect, String, Circle

def build_singing_bowls_presentation(output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Palette: Warm Gold & Dark Charcoal
    bg_color = colors.HexColor('#120E08')
    card_bg = colors.HexColor('#1E1710')
    card_border = colors.HexColor('#3D3020')
    gold_accent = colors.HexColor('#D4AF37')
    light_gold = colors.HexColor('#F3E5AB')
    text_white = colors.HexColor('#FFFFFF')
    text_muted = colors.HexColor('#D1C7BD')
    
    brand_header = ParagraphStyle('BH', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=gold_accent, spaceAfter=15)
    cover_title = ParagraphStyle('CT', fontName='Helvetica-Bold', fontSize=30, leading=36, textColor=text_white)
    cover_subtitle = ParagraphStyle('CST', fontName='Helvetica-Bold', fontSize=15, leading=20, textColor=light_gold, spaceAfter=8)
    body_muted = ParagraphStyle('BM', fontName='Helvetica', fontSize=10, leading=14, textColor=text_muted)
    sec_title = ParagraphStyle('ST', fontName='Helvetica-Bold', fontSize=22, leading=28, textColor=text_white, spaceAfter=12)
    card_hdr = ParagraphStyle('CH', fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=gold_accent, spaceAfter=4)
    card_dsc = ParagraphStyle('CD', fontName='Helvetica', fontSize=9, leading=13, textColor=text_muted)
    sku_ttl = ParagraphStyle('SKUT', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=text_white, alignment=1)
    sku_code = ParagraphStyle('SKUC', fontName='Helvetica', fontSize=9, leading=12, textColor=gold_accent, alignment=1)
    
    story = []
    
    def draw_bg(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(bg_color)
        canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=True, stroke=False)
        if doc.page > 1:
            canvas.setFont("Helvetica-Bold", 8)
            canvas.setFillColor(colors.HexColor('#8C7A6B'))
            canvas.drawString(36, 20, "OM ENTERPRISE — HANDCRAFTED HIMALAYAN SINGING BOWLS")
            canvas.drawRightString(doc.pagesize[0] - 36, 20, f"{doc.page} / 15")
        canvas.restoreState()

    # PAGE 1: COVER
    story.append(Paragraph("🕉️   O M   E N T E R P R I S E S", brand_header))
    story.append(Spacer(1, 15))
    story.append(Paragraph("HANDCRAFTED SINGING BOWLS", cover_title))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Crafted for Harmony. Made for the World.", cover_subtitle))
    story.append(Paragraph("Direct Manufacturer from Nepal | Authentic Handmade Craftsmanship", body_muted))
    story.append(Spacer(1, 30))
    
    stat_data = [
        [
            Paragraph("<b>100%</b>", ParagraphStyle('St1', fontName='Helvetica-Bold', fontSize=26, leading=30, textColor=text_white)),
            Paragraph("<b>7 Metals</b>", ParagraphStyle('St2', fontName='Helvetica-Bold', fontSize=26, leading=30, textColor=text_white)),
            Paragraph("<b>Worldwide</b>", ParagraphStyle('St3', fontName='Helvetica-Bold', fontSize=26, leading=30, textColor=text_white))
        ],
        [
            Paragraph("Handmade in Nepal", body_muted),
            Paragraph("Traditional Alloy Composition", body_muted),
            Paragraph("Export Ready Shipping", body_muted)
        ]
    ]
    t_stat = Table(stat_data, colWidths=[180, 220, 200])
    t_stat.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
    story.append(t_stat)
    story.append(PageBreak())

    # PAGE 2: BENEFITS OVERVIEW
    story.append(Paragraph("O M   E N T E R P R I S E S", brand_header))
    story.append(Paragraph("Experience Sound Harmony — Singing Bowl Benefits", sec_title))
    story.append(Paragraph(
        "Handcrafted Singing Bowls for Meditation, Sound Therapy, Healing, Relaxation &amp; Positive Energy. Manufactured with traditional craftsmanship in Nepal.",
        body_muted
    ))
    story.append(Spacer(1, 15))
    
    b1 = [Paragraph("<b>REDUCES STRESS</b>", card_hdr), Paragraph("Soothing sound promotes deep relaxation, reducing stress &amp; anxiety", card_dsc)]
    b2 = [Paragraph("<b>ENHANCES FOCUS</b>", card_hdr), Paragraph("Improves concentration, mental clarity &amp; mindfulness practice", card_dsc)]
    b3 = [Paragraph("<b>SUPPORTS MEDITATION</b>", card_hdr), Paragraph("Deepens meditation by creating a calm &amp; peaceful mind", card_dsc)]
    b4 = [Paragraph("<b>HEALING &amp; THERAPY</b>", card_hdr), Paragraph("Ideal for sound therapy, chakra healing &amp; holistic wellness", card_dsc)]
    
    t_ben = Table([[b1, b2, b3, b4]], colWidths=[175, 175, 175, 175])
    t_ben.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), card_bg),
        ('BOX', (0,0), (-1,-1), 1, card_border),
        ('INNERGRID', (0,0), (-1,-1), 1, card_border),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_ben)
    story.append(PageBreak())

    # Helper for Catalog Pages
    def build_catalog_page(p_num, title, subtitle, items_list, size_specs):
        el = []
        el.append(Paragraph(f"P A G E   {p_num}   O F   1 5", brand_header))
        el.append(Paragraph(title, sec_title))
        el.append(Paragraph(subtitle, body_muted))
        el.append(Spacer(1, 12))
        
        row_cells = []
        c_width = 175 if len(items_list) >= 4 else 235
        for name, code in items_list:
            d = Drawing(c_width - 20, 95)
            d.add(Rect(0, 0, c_width - 20, 95, fillColor=colors.HexColor('#2A2016'), strokeColor=card_border, rx=6, ry=6))
            d.add(Circle((c_width - 20)/2, 48, 22, fillColor=colors.HexColor('#3E3020'), strokeColor=gold_accent))
            d.add(String((c_width - 20)/2, 44, "🥣", fontName="Helvetica", fontSize=18, textAnchor="middle"))
            row_cells.append([d, Spacer(1, 4), Paragraph(name, sku_ttl), Paragraph(code, sku_code)])
            
        t_items = Table([row_cells], colWidths=[c_width] * len(items_list))
        t_items.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), card_bg),
            ('BOX', (0,0), (-1,-1), 1, card_border),
            ('INNERGRID', (0,0), (-1,-1), 1, card_border),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER')
        ]))
        el.append(t_items)
        el.append(Spacer(1, 12))
        
        t_spec = Table([[Paragraph(f"<b>Specifications / Available Sizes:</b> {size_specs}", ParagraphStyle('SP', fontName='Helvetica', fontSize=9, textColor=light_gold))]], colWidths=[710])
        t_spec.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#18130B')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#382C1C')),
            ('PADDING', (0,0), (-1,-1), 8),
            ('ALIGN', (0,0), (-1,-1), 'LEFT')
        ]))
        el.append(t_spec)
        el.append(PageBreak())
        return el

    # PAGES 3-12: PRODUCTS
    story.extend(build_catalog_page(3, "The Harmony of Singing Bowls", "Authentic, handcrafted instruments elevating meditation centers, sound therapy &amp; yoga studios worldwide.", [("Handmade Authentic", "HM-SERIES"), ("Machine Casted", "MC-SERIES"), ("Sound Therapy Set", "ST-SERIES")], "Authentic 7-metal alloy craftsmanship handcrafted in Nepal."))
    story.extend(build_catalog_page(4, "Product Preview: Handmade vs Machine Made", "Complete range covering authentic hand-beaten bowls and precision machine casted bowls.", [("Hand Beaten Bowls", "HM-PREVIEW"), ("Machine Casted Bowls", "MC-PREVIEW"), ("Gongs &amp; Accessories", "ACC-PREVIEW")], "Handmade: Antique &amp; Mantra carved. Machine Made: Hammered &amp; Plain."))
    story.extend(build_catalog_page(5, "Handmade Singing Bowl 'ANTIQUE FINISH'", "CODE: #HM-PLN", [("Small Antique (4-5.5\")", "HM-PLN-S"), ("Medium Antique (6-11\")", "HM-PLN-M"), ("Large Antique (12-20\")", "HM-PLN-L"), ("XL Antique (20-24\")", "HM-PLN-XL")], "Small: 350-550g | Medium: 630g-2.5kg | Large: 3-11kg | XL: 10.5-20kg | 26\": 21-22kg | 30\": 35-36kg."))
    story.extend(build_catalog_page(6, "Handmade Singing Bowl (Mantra &amp; Buddha Carved)", "CODE: #HM-EC", [("Small Carved (4-5.5\")", "HM-EC-S"), ("Medium Carved (6-11\")", "HM-EC-M"), ("Large Carved (12-20\")", "HM-EC-L"), ("XL Carved (20-24\")", "HM-EC-XL")], "Intricate hand carving of sacred Tibetan Om Mani Padme Hum mantras and Buddha figures."))
    story.extend(build_catalog_page(7, "Professional Chakra Sets (7 Pcs CDEFGAB)", "CODE: #HM-7", [("Medium Chakra Set (6-10.5\")", "HM-7-MED"), ("Large Chakra Set (8-14\")", "HM-7-LRG")], "Medium Set: 10.5 - 11.65 kg | Large Set: 16.5 - 17.5 kg. Includes wooden mallets &amp; ring cushions."))
    story.extend(build_catalog_page(8, "Handmade Gongs - Plain &amp; Carved", "CODE: #GNG", [("Gong Plain Antique (18\")", "GNG-PLN-18"), ("Gong Plain Antique (24-26\")", "GNG-PLN-24"), ("Gong Mantra Carved (18\")", "GNG-CRV-18"), ("Gong Mantra Carved (24-26\")", "GNG-CRV-24")], "18 Inch: 2.5 - 2.75 kg | 24 to 26 Inch: 5.5 - 6.0 kg. Professionally tuned for sound baths."))
    story.extend(build_catalog_page(9, "Machine Made (Casted) Singing Bowls", "Hammered &amp; Polished Finish", [("Casted Hammered 4\"", "MC-HMR-4"), ("Casted Hammered 5\"", "MC-HMR-5"), ("Casted Hammered 6\"", "MC-HMR-6")], "High-volume uniform manufacturing suitable for beginner sets, retail chains &amp; gifting."))
    story.extend(build_catalog_page(10, "Machine Made (Casted) Mantra Decoration", "CODE: #CT (Breakable Warning)", [("Casted Mantra 3.5\"", "CT-35"), ("Casted Mantra 4\"", "CT-40"), ("Casted Mantra 5\"", "CT-50"), ("Casted Mantra 5.5\"", "CT-55")], "3.5\": 350g | 4\": 500g | 5\": 700g | 5.5\": 1kg. Complete with ring cushion and wooden stick."))
    story.extend(build_catalog_page(11, "Meditation Bell (Tingsha &amp; Hand Bells)", "CODE: #CSTD-BLS", [("Bell 3\" x 5\"", "BLS-30"), ("Bell 3.5\" x 6.5\"", "BLS-35"), ("Bell 4\" x 7\"", "BLS-40"), ("Bell 4.5\" x 8\"", "BLS-45")], "Traditional bronze bell for meditation, temple rituals &amp; sound clearing."))
    story.extend(build_catalog_page(12, "Happy Drum (Steel Tongue Drum)", "Professionally Tuned Sound Therapy Instrument", [("Happy Drum 6 Inch", "DRM-6"), ("Happy Drum 8 Inch", "DRM-8"), ("Happy Drum 10 Inch", "DRM-10")], "Available in 6\", 8\", 10\" diameters. Includes rubber mallets and songbook."))

    # PAGE 13: CONTACT / CTA
    story.append(Paragraph("L E T ' S   W O R K   T O G E T H E R", brand_header))
    story.append(Paragraph("Ready to Elevate Your Space?", sec_title))
    story.append(Paragraph("Contact us for wholesale pricing catalogs, custom studio packages, and expert sound therapy consultations.", body_muted))
    story.append(Spacer(1, 15))
    
    fc1 = [Paragraph("<b>Direct Manufacturer</b>", card_hdr), Paragraph("Handmade in Nepal with authentic craftsmanship", card_dsc)]
    fc2 = [Paragraph("<b>Wholesale &amp; Bulk Supply</b>", card_hdr), Paragraph("Factory-direct FOB pricing for global distributors", card_dsc)]
    fc3 = [Paragraph("<b>OEM &amp; Private Label</b>", card_hdr), Paragraph("Custom logo engraving &amp; custom packaging", card_dsc)]
    
    t_cta = Table([[fc1, fc2, fc3]], colWidths=[235, 235, 235])
    t_cta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), card_bg),
        ('BOX', (0,0), (-1,-1), 1, card_border),
        ('INNERGRID', (0,0), (-1,-1), 1, card_border),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_cta)
    story.append(Spacer(1, 15))
    
    c_info = Paragraph(
        "<b>OM ENTERPRISE</b><br/>"
        "📧 exportindia2026us@gmail.com | 📱 +91 80577 10065 | 🌐 www.omenterprise.com",
        ParagraphStyle('CInfo', fontName='Helvetica-Bold', fontSize=11, leading=16, textColor=light_gold, alignment=1)
    )
    t_foot = Table([[c_info]], colWidths=[710])
    t_foot.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1E1710')),
        ('BOX', (0,0), (-1,-1), 1, card_border),
        ('PADDING', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    story.append(t_foot)
    story.append(PageBreak())

    # PAGE 14: SOUND HEALING BENEFITS
    story.append(Paragraph("S O U N D   H E A L I N G   B E N E F I T S", brand_header))
    story.append(Paragraph("10 Core Health &amp; Wellness Benefits", sec_title))
    story.append(Spacer(1, 10))
    
    b_list = [
        "1. Relief from stress and anxiety",
        "2. Fewer headaches & tension relief",
        "3. Boost in confidence & mental clarity",
        "4. Gives you more focus & concentration",
        "5. Increased vital energy & stamina",
        "6. Improved relationships & emotional balance",
        "7. Think more clearly & make better decisions",
        "8. Improve organization skills & mindfulness",
        "9. Improved attention span during meditation",
        "10. Get relief from common physical ailments"
    ]
    
    b_cells = [[Paragraph(f"• <b>{item}</b>", ParagraphStyle('BItem', fontName='Helvetica', fontSize=11, leading=16, textColor=text_white))] for item in b_list]
    t_blist = Table([b_cells[:5], b_cells[5:]], colWidths=[350, 350])
    t_blist.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), card_bg),
        ('BOX', (0,0), (-1,-1), 1, card_border),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    story.append(t_blist)
    story.append(PageBreak())

    # PAGE 15: THANK YOU
    story.append(Spacer(1, 80))
    story.append(Paragraph("THANK YOU", ParagraphStyle('TY', fontName='Helvetica-Bold', fontSize=42, leading=48, textColor=gold_accent, alignment=1)))
    story.append(Spacer(1, 15))
    story.append(Paragraph("We look forward to exploring a potential long-term business partnership.", ParagraphStyle('TYS', fontName='Helvetica', fontSize=14, leading=18, textColor=text_white, alignment=1)))
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>OM ENTERPRISE</b> — Authentic Handmade Himalayan Singing Bowls", ParagraphStyle('TYB', fontName='Helvetica', fontSize=12, leading=16, textColor=light_gold, alignment=1)))

    doc.build(story, onFirstPage=draw_bg, onLaterPages=draw_bg)
    print(f"Presentation PDF compiled to {output_path}")

def build_singing_bowls_poster_image(output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 800 x 1130 px high quality poster graphic matching user poster layout
    width, height = 800, 1130
    img = Image.new('RGB', (width, height), color='#FAF6EE')
    draw = ImageDraw.Draw(img)
    
    # Colors
    gold = '#B8860B'
    dark_gold = '#8B6508'
    bg_dark = '#120E08'
    text_dark = '#2A2016'
    maroon_bg = '#6B1610'
    white = '#FFFFFF'
    
    # Top Header
    draw.rectangle([(0, 0), (width, 90)], fill='#F4EAD5')
    draw.text((40, 20), "🕉️ OM ENTERPRISE", fill=dark_gold, font_size=28)
    draw.text((40, 55), "DIRECT MANUFACTURER FROM NEPAL", fill=text_dark, font_size=14)
    
    # Hero Title Box
    draw.rectangle([(40, 110), (width - 40, 240)], fill=bg_dark)
    draw.text((60, 125), "AUTHENTIC HANDMADE", fill='#E5C158', font_size=24)
    draw.text((60, 155), "HIMALAYAN SINGING BOWLS", fill=white, font_size=32)
    draw.text((60, 200), "WHOLESALE  •  OEM  •  PRIVATE LABEL", fill=gold, font_size=16)
    
    # Highlights Row
    highlights = [
        "DIRECT MANUFACTURER\nfrom Nepal",
        "AUTHENTIC HANDMADE\nCraftsmanship",
        "OEM & PRIVATE LABEL\nServices Available",
        "WORLDWIDE SHIPPING\nReliable & Safe",
        "DEDICATED EXPORT\nSupport Every Step"
    ]
    box_w = 135
    for i, hl in enumerate(highlights):
        x = 40 + i * (box_w + 10)
        draw.rectangle([(x, 260), (x + box_w, 330)], fill='#EFE3CF', outline=dark_gold, width=1)
        draw.text((x + 8, 270), hl, fill=text_dark, font_size=10)
        
    # Section Header: COLLECTIONS
    draw.rectangle([(40, 350), (width - 40, 380)], fill='#D4AF37')
    draw.text((width // 2, 358), "OUR COLLECTIONS", fill=bg_dark, font_size=16, anchor="mm")
    
    # Collection Cards
    draw.rectangle([(40, 395), (390, 510)], fill=maroon_bg)
    draw.text((60, 410), "PREMIUM COLLECTION", fill='#F3E5AB', font_size=16)
    draw.text((60, 435), "Handcrafted with excellence.\nNo Minimum Order Quantity", fill=white, font_size=12)
    
    draw.rectangle([(410, 395), (width - 40, 510)], fill='#1F3320')
    draw.text((430, 410), "STANDARD COLLECTION", fill='#F3E5AB', font_size=16)
    draw.text((430, 435), "Perfect for wholesalers & distributors.\nMOQ: 200 Pieces", fill=white, font_size=12)
    
    # Section Header: PRODUCT RANGE
    draw.rectangle([(40, 525), (width - 40, 555)], fill='#D4AF37')
    draw.text((width // 2, 533), "OUR PRODUCT RANGE", fill=bg_dark, font_size=16, anchor="mm")
    
    products = [
        "HANDMADE HIMALAYAN\nSINGING BOWLS",
        "FULL MOON\nSINGING BOWLS",
        "ANTIQUE FINISH\nSINGING BOWLS",
        "CHAKRA SINGING\nBOWL SETS",
        "MEDITATION &\nSOUND HEALING BOWLS",
        "TINGSHA CYMBALS &\nMEDITATION ACCESSORIES",
        "CUSTOM LOGO &\nPRIVATE LABEL"
    ]
    
    p_box_w = 95
    for i, p in enumerate(products):
        x = 40 + i * (p_box_w + 9)
        draw.rectangle([(x, 570), (x + p_box_w, 660)], fill='#F0E5D3', outline=dark_gold, width=1)
        draw.text((x + 6, 580), p, fill=text_dark, font_size=9)
        
    # Why Partner Box
    draw.rectangle([(40, 680), (width - 40, 770)], fill='#E6D9C3')
    draw.text((60, 690), "WHY PARTNER WITH OM ENTERPRISE?", fill=dark_gold, font_size=14)
    reasons = "✔ Direct Manufacturer from Nepal  ✔ Authentic Handmade Craftsmanship  ✔ OEM & Private Label\n✔ Worldwide Reliable Shipping  ✔ Dedicated Export Support  ✔ Sample Orders Available"
    draw.text((60, 715), reasons, fill=text_dark, font_size=12)
    
    # Footer Banner
    draw.rectangle([(40, 785), (width - 40, 860)], fill=maroon_bg)
    draw.text((60, 800), "REPLY TO THIS EMAIL", fill='#F3E5AB', font_size=18)
    draw.text((60, 828), "for wholesale pricing, samples & shipping quotations.", fill=white, font_size=13)
    draw.text((width - 60, 815), "LET'S CREATE HARMONY TOGETHER", fill='#F3E5AB', font_size=14, anchor="rm")
    
    # Contact Footer
    draw.rectangle([(0, 875), (width, height)], fill=bg_dark)
    draw.text((60, 910), "OM ENTERPRISE", fill='#E5C158', font_size=22)
    draw.text((60, 945), "📧 exportindia2026us@gmail.com", fill=white, font_size=14)
    draw.text((60, 975), "📱 +91 80577 10065", fill=white, font_size=14)
    draw.text((60, 1005), "🌐 www.omenterprise.com", fill=gold, font_size=14)
    draw.text((width - 60, 950), "Authentic Products.\nHonest Business.\nLong Term Partnership.", fill='#D1C7BD', font_size=14, anchor="rm")


    img.save(output_path)
    print(f"Product Poster image created at {output_path}")

if __name__ == '__main__':
    base_assets = os.path.join(os.path.dirname(__file__), 'assets')
    build_singing_bowls_presentation(os.path.join(base_assets, 'company_presentation.pdf'))
    build_singing_bowls_poster_image(os.path.join(base_assets, 'product_poster.jpg'))
